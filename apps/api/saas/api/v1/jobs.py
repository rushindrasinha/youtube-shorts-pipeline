"""Jobs API endpoints — create, list, detail, cancel, retry, SSE progress."""

import json
from typing import Optional
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ...api.deps import get_current_user, get_db
from ...models.user import User
from ...schemas.common import ErrorDetail, ErrorResponse
from ...schemas.job import (
    JobCreate,
    JobDetailResponse,
    JobResponse,
    JobStageResponse,
    PaginatedJobs,
)
from ...services.job_service import (
    cancel_job,
    create_job,
    get_job_detail,
    get_user_jobs,
    retry_job,
)
from ...services.usage_service import check_can_create_job
from ...settings import settings

router = APIRouter()


@router.post("/jobs", response_model=JobResponse, status_code=202)
async def create_new_job(
    data: JobCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new video generation job and enqueue it to Celery."""
    # Check usage limits
    allowed, reason = check_can_create_job(db, user)
    if not allowed:
        raise HTTPException(
            status_code=402,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="INSUFFICIENT_QUOTA",
                    message=reason,
                )
            ).model_dump(),
        )

    # Create job in DB
    job = create_job(db, user, data)

    # Enqueue to Celery (deferred import to avoid circular deps in tests)
    try:
        from saas.tasks.pipeline_task import run_video_pipeline

        # Only enqueue immediately if not scheduled for the future
        if not data.scheduled_at:
            task = run_video_pipeline.apply_async(
                args=[str(job.id)],
                queue="video",
                retry=False,
            )
            job.celery_task_id = task.id
            db.commit()
    except Exception:
        # If Celery is unavailable, job stays queued and will be picked up later
        pass

    return JobResponse.model_validate(job)


@router.get("/jobs", response_model=PaginatedJobs)
async def list_jobs(
    status: Optional[str] = Query(None, pattern="^(queued|running|completed|failed|canceled)$"),
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the current user's jobs with cursor pagination."""
    items, next_cursor, has_more = get_user_jobs(
        db, user.id, status=status, cursor=cursor, limit=limit
    )
    return PaginatedJobs(
        items=[JobResponse.model_validate(j) for j in items],
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: UUID,
    include: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get job details with stages. Use ?include=draft_data for full draft."""
    include_fields = include.split(",") if include else []

    job = get_job_detail(db, user.id, job_id, include_fields=include_fields)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=ErrorDetail(code="NOT_FOUND", message="Job not found")
            ).model_dump(),
        )

    stages = [
        JobStageResponse(
            name=s.stage_name,
            status=s.status,
            duration_ms=s.duration_ms,
        )
        for s in sorted(job.stages, key=lambda s: s.stage_name)
    ]

    response = JobDetailResponse(
        id=job.id,
        topic=job.topic,
        status=job.status,
        progress_pct=job.progress_pct,
        current_stage=job.current_stage,
        created_at=job.created_at,
        completed_at=job.completed_at,
        cost_usd=float(job.cost_usd),
        stages=stages,
        error_message=job.error_message,
        draft_data=job.draft_data if "draft_data" in include_fields else None,
    )
    return response


@router.delete("/jobs/{job_id}", response_model=JobResponse)
async def cancel_existing_job(
    job_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a queued or running job."""
    job = cancel_job(db, user.id, job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=ErrorDetail(code="NOT_FOUND", message="Job not found")
            ).model_dump(),
        )

    # Revoke Celery task if we have a task ID
    if job.celery_task_id:
        try:
            from saas.workers.celery_app import app as celery_app

            celery_app.control.revoke(job.celery_task_id, terminate=True)
        except Exception:
            pass  # Best effort

    return JobResponse.model_validate(job)


@router.post("/jobs/{job_id}/retry", response_model=JobResponse)
async def retry_failed_job(
    job_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retry a failed job by re-enqueueing it."""
    from ...models.job import Job

    # First check the job exists and belongs to user
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=ErrorDetail(code="NOT_FOUND", message="Job not found")
            ).model_dump(),
        )

    if job.status != "failed":
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_INPUT",
                    message="Only failed jobs can be retried",
                )
            ).model_dump(),
        )

    job = retry_job(db, user.id, job_id)

    # Enqueue to Celery
    try:
        from saas.tasks.pipeline_task import run_video_pipeline

        task = run_video_pipeline.apply_async(
            args=[str(job.id)],
            queue="video",
            retry=False,
        )
        job.celery_task_id = task.id
        db.commit()
    except Exception:
        pass

    return JobResponse.model_validate(job)


@router.get("/jobs/{job_id}/events")
async def job_events(
    job_id: UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SSE endpoint for real-time job progress updates via Redis pub/sub."""
    from ...models.job import Job

    # Verify user owns this job
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=ErrorDetail(code="NOT_FOUND", message="Job not found")
            ).model_dump(),
        )

    # If job is already in a terminal state, send final event immediately
    if job.status in ("completed", "failed", "canceled"):
        async def terminal_stream():
            event_type = f"job_{job.status}"
            data = json.dumps({
                "type": event_type,
                "progress_pct": job.progress_pct,
                "status": job.status,
            })
            yield f"event: {event_type}\ndata: {data}\n\n"

        return StreamingResponse(
            terminal_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    async def event_stream():
        r = aioredis.from_url(settings.REDIS_URL)
        pubsub = r.pubsub()
        await pubsub.subscribe(f"job:{job_id}")

        try:
            async for message in pubsub.listen():
                # Check if client disconnected
                if await request.is_disconnected():
                    break

                if message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode()

                    parsed = json.loads(data)
                    event_type = parsed.get("type", "progress")
                    yield f"event: {event_type}\ndata: {data}\n\n"

                    # Close stream on terminal events
                    if event_type in ("job_completed", "job_failed", "job_error"):
                        break
        finally:
            await pubsub.unsubscribe(f"job:{job_id}")
            await r.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
