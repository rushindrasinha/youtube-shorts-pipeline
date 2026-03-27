"""Trending topics API endpoints — cached topics and quick-create."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...api.deps import get_current_user, get_db
from ...models.topic_cache import TrendingTopicCache
from ...models.user import User
from ...schemas.common import ErrorDetail, ErrorResponse
from ...schemas.job import JobCreate, JobResponse
from ...schemas.topic import (
    QuickCreateRequest,
    TrendingTopicResponse,
    TrendingTopicsListResponse,
)
from ...services.job_service import create_job
from ...services.usage_service import check_can_create_job

router = APIRouter()


@router.get("/topics/trending")
def get_trending_topics(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return cached trending topics from the database.

    Topics are refreshed by a periodic Celery task every 15 minutes.
    """
    now = datetime.now(timezone.utc)

    topics = (
        db.query(TrendingTopicCache)
        .filter(TrendingTopicCache.expires_at > now)
        .order_by(TrendingTopicCache.trending_score.desc())
        .limit(50)
        .all()
    )

    items = []
    latest_fetch = None
    for t in topics:
        items.append(
            TrendingTopicResponse(
                title=t.title,
                source=t.source,
                trending_score=float(t.trending_score),
                summary=t.summary,
                url=t.url,
                metadata=t.extra_metadata or {},
            )
        )
        if latest_fetch is None or t.fetched_at > latest_fetch:
            latest_fetch = t.fetched_at

    return TrendingTopicsListResponse(
        items=items,
        cached_at=latest_fetch,
        next_refresh_at=latest_fetch + timedelta(minutes=15)
        if latest_fetch
        else None,
    )


@router.post("/topics/quick-create", status_code=202)
def quick_create(
    body: QuickCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a video generation job directly from a trending topic title."""
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

    # Build a JobCreate from the topic title
    job_data = JobCreate(
        topic=body.topic_title,
        channel_id=body.channel_id,
    )
    job = create_job(db, user, job_data)

    # Enqueue to Celery
    try:
        from saas.tasks.pipeline_task import run_video_pipeline

        task = run_video_pipeline.apply_async(
            args=[str(job.id)],
            queue="video",
        )
        job.celery_task_id = task.id
        db.commit()
    except Exception:
        pass  # Job stays queued, will be picked up later

    return JobResponse.model_validate(job)


@router.post("/topics/refresh")
def refresh_topics(user=Depends(get_current_user)):
    from saas.tasks.topic_task import refresh_trending_topics
    refresh_trending_topics.delay()
    return {"status": "refreshing"}
