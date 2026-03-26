"""Job lifecycle service — create, list, detail, cancel, retry."""

import base64
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from ..models.job import Job, JobStage
from ..models.user import User
from ..schemas.job import JobCreate

# Pipeline stages in execution order
PIPELINE_STAGES = [
    "research", "draft", "broll", "voiceover",
    "captions", "music", "assemble", "thumbnail",
]


def create_job(db: Session, user: User, data: JobCreate) -> Job:
    """Create a new Job with initial pending JobStage records."""
    job = Job(
        user_id=user.id,
        topic=data.topic,
        context=data.context,
        language=data.language,
        voice_id=data.voice_id or None,
        caption_style=data.caption_style,
        music_genre=data.music_genre,
        channel_id=data.channel_id,
        auto_upload=data.auto_upload,
        upload_privacy=data.upload_privacy,
        scheduled_at=data.scheduled_at,
        status="queued",
        progress_pct=0,
    )
    db.add(job)
    db.flush()  # Populate job.id

    # Create initial stage records
    for stage_name in PIPELINE_STAGES:
        stage = JobStage(
            job_id=job.id,
            stage_name=stage_name,
            status="pending",
        )
        db.add(stage)

    db.commit()
    db.refresh(job)
    return job


def get_user_jobs(
    db: Session,
    user_id: UUID,
    status: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = 20,
) -> tuple[list[Job], Optional[str], bool]:
    """Return paginated jobs for a user. Uses cursor-based pagination (no total count).

    Cursor is base64-encoded created_at timestamp of the last item.
    Returns (items, next_cursor, has_more).
    """
    query = db.query(Job).filter(Job.user_id == user_id)

    if status:
        query = query.filter(Job.status == status)

    # Decode cursor — it's the created_at of the last seen item
    if cursor:
        try:
            cursor_bytes = base64.urlsafe_b64decode(cursor)
            cursor_dt = datetime.fromisoformat(cursor_bytes.decode())
            query = query.filter(Job.created_at < cursor_dt)
        except Exception:
            pass  # Ignore invalid cursor

    query = query.order_by(desc(Job.created_at))

    # Fetch one extra to check has_more
    jobs = query.limit(limit + 1).all()

    has_more = len(jobs) > limit
    items = jobs[:limit]

    next_cursor = None
    if has_more and items:
        last_created = items[-1].created_at.isoformat()
        next_cursor = base64.urlsafe_b64encode(last_created.encode()).decode()

    return items, next_cursor, has_more


def get_job_detail(
    db: Session,
    user_id: UUID,
    job_id: UUID,
    include_fields: Optional[list[str]] = None,
) -> Optional[Job]:
    """Load a single job with stages. Optionally include draft_data."""
    job = (
        db.query(Job)
        .options(joinedload(Job.stages))
        .filter(Job.id == job_id, Job.user_id == user_id)
        .first()
    )
    return job


def cancel_job(db: Session, user_id: UUID, job_id: UUID) -> Optional[Job]:
    """Cancel a queued or running job."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()
    if not job:
        return None

    if job.status not in ("queued", "running"):
        return job  # Can't cancel completed/failed/canceled jobs

    job.status = "canceled"
    job.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job


def retry_job(db: Session, user_id: UUID, job_id: UUID) -> Optional[Job]:
    """Retry a failed job by resetting its status and re-enqueueing."""
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user_id).first()
    if not job:
        return None

    if job.status != "failed":
        return job  # Can only retry failed jobs

    job.status = "queued"
    job.progress_pct = 0
    job.current_stage = None
    job.error_message = None
    job.retry_count += 1
    job.completed_at = None
    job.started_at = None
    job.celery_task_id = None

    # Reset all stages to pending
    for stage in job.stages:
        stage.status = "pending"
        stage.started_at = None
        stage.completed_at = None
        stage.duration_ms = None
        stage.error_message = None

    db.commit()
    db.refresh(job)
    return job
