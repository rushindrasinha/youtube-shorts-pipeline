"""Main Celery task for running the video generation pipeline."""

import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import redis
from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession

from saas.workers.celery_app import app

logger = get_task_logger(__name__)


@app.task(bind=True, max_retries=1, soft_time_limit=840, time_limit=900)
def run_video_pipeline(self, job_id: str):
    """Execute the full video generation pipeline for a job.

    This task:
    1. Reads job config from PostgreSQL
    2. Resolves API keys (platform or BYOK)
    3. Runs pipeline stages with progress callbacks
    4. Updates job record with results
    5. Publishes progress events to Redis for SSE delivery
    """
    from saas.settings import settings
    from saas.models.job import Job, JobStage
    from saas.services.key_service import resolve_api_keys
    from pipeline.adapter import PipelineJob
    from pipeline.config import JobConfig

    # Create a dedicated DB session for this task
    engine = create_engine(settings.DATABASE_URL)
    db = SASession(engine)

    work_dir = None

    try:
        # 1. Load job from database
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.celery_task_id = self.request.id
        db.commit()

        # 2. Resolve API keys (platform defaults or user's BYOK)
        keys = resolve_api_keys(db, job.user_id)

        # 3. Create work directory
        work_dir = Path(tempfile.mkdtemp(prefix=f"sf_{job_id[:8]}_"))

        # 4. Build progress callback
        def on_progress(stage: str, status: str, pct: int, artifacts: dict):
            """Update DB + publish to Redis for SSE."""
            _update_job_progress(db, job, stage, status, pct, artifacts)
            _publish_progress(str(job_id), stage, status, pct)

        # 5. Build pipeline config
        config = JobConfig(
            job_id=str(job_id),
            work_dir=work_dir,
            topic=job.topic,
            context=job.context or "",
            anthropic_api_key=keys["anthropic"],
            gemini_api_key=keys["gemini"],
            elevenlabs_api_key=keys.get("elevenlabs", ""),
            voice_id=job.voice_id or "JBFqnCBsd6RMkjVDRZzb",
            language=job.language or "en",
            caption_style=job.caption_style or "yellow_highlight",
            music_genre=job.music_genre or "auto",
            on_progress=on_progress,
        )

        # 6. Run pipeline
        pipeline_job = PipelineJob(config)
        result = pipeline_job.run()

        if result["status"] == "completed":
            # Update job as completed
            job.status = "completed"
            job.progress_pct = 100
            job.draft_data = result.get("draft", {})
            job.completed_at = datetime.now(timezone.utc)
            db.commit()

            # Publish completion event
            _publish_progress(str(job_id), "completed", "done", 100)

        else:
            # Pipeline failed
            job.status = "failed"
            job.error_message = result.get("error", "Unknown error")
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            _publish_progress(str(job_id), "failed", "error", job.progress_pct)

    except SoftTimeLimitExceeded:
        job.status = "failed"
        job.error_message = "Job timed out (exceeded 14 minutes)"
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        _publish_progress(str(job_id), "timeout", "error", job.progress_pct)

    except Exception as e:
        logger.exception(f"Job {job_id} failed with exception")
        try:
            job.status = "failed"
            job.error_message = str(e)[:500]
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            _publish_progress(str(job_id), "error", "error", job.progress_pct)
        except Exception:
            logger.exception("Failed to update job status after error")

        # Retry once on transient errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30)

    finally:
        db.close()
        engine.dispose()
        # Clean up temp files
        if work_dir and work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)


def _update_job_progress(db, job, stage, status, pct, artifacts):
    """Update job record with stage progress."""
    from saas.models.job import JobStage

    job.current_stage = stage
    job.progress_pct = pct

    # Upsert job_stage record
    job_stage = db.query(JobStage).filter(
        JobStage.job_id == job.id,
        JobStage.stage_name == stage,
    ).first()

    if not job_stage:
        job_stage = JobStage(
            job_id=job.id,
            stage_name=stage,
        )
        db.add(job_stage)

    if status == "running":
        job_stage.status = "running"
        job_stage.started_at = datetime.now(timezone.utc)
    elif status == "done":
        job_stage.status = "done"
        job_stage.completed_at = datetime.now(timezone.utc)
        if job_stage.started_at:
            delta = job_stage.completed_at - job_stage.started_at
            job_stage.duration_ms = int(delta.total_seconds() * 1000)
        if artifacts:
            job_stage.artifacts = artifacts

    db.commit()


def _publish_progress(job_id: str, stage: str, status: str, pct: int):
    """Publish progress event to Redis pub/sub for SSE delivery."""
    try:
        r = redis.from_url("redis://localhost:6379/0")
        r.publish(f"job:{job_id}", json.dumps({
            "type": f"stage_{status}" if status in ("running", "done") else f"job_{status}",
            "stage": stage,
            "progress_pct": pct,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }))
        r.close()
    except Exception:
        # Don't fail the pipeline if Redis publish fails
        logger.warning(f"Failed to publish progress for job {job_id}")
