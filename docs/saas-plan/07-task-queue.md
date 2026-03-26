# 07 — Task Queue & Job Orchestration

## Architecture

```
API Server ─→ Redis (broker) ─→ Celery Workers ─→ Redis (pub/sub) ─→ WebSocket Manager
                                      │
                                PostgreSQL (job records)
                                      │
                                S3 (artifacts)
```

---

## Celery Configuration

```python
# saas/workers/celery_app.py

from celery import Celery
from celery.signals import worker_init

app = Celery("shortfactory")

app.config_from_object({
    "broker_url": "redis://localhost:6379/0",
    "result_backend": "redis://localhost:6379/1",
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "timezone": "UTC",
    "task_track_started": True,

    # Queues: separate priority levels
    "task_routes": {
        "saas.tasks.pipeline_task.run_video_pipeline": {"queue": "video"},
        "saas.tasks.pipeline_task.run_video_pipeline_priority": {"queue": "video_priority"},
        "saas.tasks.cleanup_task.*": {"queue": "maintenance"},
        "saas.tasks.billing_task.*": {"queue": "maintenance"},
        "saas.tasks.topic_task.*": {"queue": "maintenance"},
    },

    # Concurrency limits
    "worker_concurrency": 2,           # 2 concurrent video jobs per worker (FFmpeg+Whisper are CPU-bound; scale horizontally)
    "task_time_limit": 900,            # 15 min hard limit (pipeline with retries can take 7+ min)
    "task_soft_time_limit": 840,       # 14 min soft limit (raises SoftTimeLimitExceeded)

    # Retry configuration
    "task_acks_late": True,            # Acknowledge after task completes (crash safety)
    "worker_prefetch_multiplier": 1,   # Don't prefetch — video jobs are long-running
    "task_reject_on_worker_lost": True, # If worker OOM-killed, return task to queue (not stuck forever)

    # Result expiry
    "result_expires": 86400,           # 24 hours
})


@worker_init.connect
def init_worker(**kwargs):
    """Called when a Celery worker starts.

    NOTE: Whisper model is NOT pre-loaded here. It is cached at module level
    in pipeline/captions.py (_get_whisper_model). Loading in two places wastes
    memory and creates confusion about which global is used. The captions module
    cache is the single source of truth.

    Use faster-whisper (CTranslate2) instead of openai-whisper for 4x speedup
    and 4x less memory on CPU.
    """
    print("Worker initialized.")
```

---

## Queue Architecture

### Three Queue Tiers

| Queue | Purpose | Workers | Concurrency |
|-------|---------|---------|-------------|
| `video_priority` | Pro/Agency/Enterprise jobs | Dedicated workers | 4/worker |
| `video` | Free/Creator tier jobs | Shared workers | 4/worker |
| `maintenance` | Cleanup, billing sync, topic refresh | 1 worker | 2 |

Priority queue ensures paid users never wait behind free-tier jobs.

```bash
# Start workers for each queue
celery -A saas.workers.celery_app worker -Q video_priority -c 4 --hostname=priority@%h
celery -A saas.workers.celery_app worker -Q video -c 4 --hostname=default@%h
celery -A saas.workers.celery_app worker -Q maintenance -c 2 --hostname=maintenance@%h
```

---

## Main Pipeline Task

```python
# saas/tasks/pipeline_task.py

import shutil
import tempfile
from pathlib import Path
from uuid import UUID

from celery import shared_task
from celery.utils.log import get_task_logger

from saas.workers.celery_app import app

logger = get_task_logger(__name__)


@app.task(bind=True, max_retries=1, soft_time_limit=540, time_limit=600)
def run_video_pipeline(self, job_id: str):
    """Execute the full video generation pipeline for a job.

    This task:
    1. Reads job config from PostgreSQL
    2. Resolves API keys (platform or BYOK)
    3. Runs pipeline stages with progress callbacks
    4. Uploads artifacts to S3
    5. Updates job record with results
    6. Optionally uploads to YouTube
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SASession
    from saas.settings import settings
    from saas.models.job import Job, JobStage
    from saas.models.subscription import Subscription
    from saas.services.storage_service import StorageService
    from saas.services.key_service import resolve_api_keys
    from saas.services.usage_service import UsageService
    from saas.utils.encryption import decrypt_value
    from pipeline.adapter import PipelineJob
    from pipeline.config import JobConfig

    # Create a dedicated DB session for this task
    engine = create_engine(settings.DATABASE_URL)
    db = SASession(engine)

    try:
        # 1. Load job from database
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = "running"
        job.celery_task_id = self.request.id
        db.commit()

        # 2. Resolve API keys (platform defaults or user's BYOK)
        keys = resolve_api_keys(db, job.user_id)

        # 3. Create work directory
        work_dir = Path(tempfile.mkdtemp(prefix=f"sf_{job_id[:8]}_"))

        # 4. Build progress callback
        def on_progress(stage: str, status: str, pct: int, artifacts: dict):
            """Update DB + publish to Redis for WebSocket."""
            _update_job_progress(db, job, stage, status, pct, artifacts)
            _publish_progress(job_id, stage, status, pct)

        # 5. Build pipeline config
        config = JobConfig(
            job_id=job_id,
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
            # 7. Upload artifacts to S3
            storage = StorageService()
            month = datetime.now(timezone.utc).strftime("%Y-%m")
            user_prefix = f"{job.user_id}/{month}/{job_id}"

            video_url = storage.upload_file(
                result["video_path"],
                f"{user_prefix}/final.mp4",
                content_type="video/mp4",
            )

            thumbnail_url = None
            if result.get("thumbnail_path"):
                thumbnail_url = storage.upload_file(
                    result["thumbnail_path"],
                    f"{user_prefix}/thumbnail.png",
                    content_type="image/png",
                )

            srt_url = None
            if result.get("srt_path"):
                srt_url = storage.upload_file(
                    result["srt_path"],
                    f"{user_prefix}/captions.srt",
                    content_type="text/plain",
                )

            # 8. Create Video record
            from saas.models.video import Video
            video = Video(
                job_id=job.id,
                user_id=job.user_id,
                team_id=job.team_id,
                channel_id=job.channel_id,
                title=result["draft"].get("youtube_title", job.topic)[:200],
                description=result["draft"].get("youtube_description", ""),
                tags=result["draft"].get("youtube_tags", "").split(","),
                script=result["draft"].get("script", ""),
                language=job.language,
                video_url=video_url["public_url"],
                video_s3_key=video_url["s3_key"],
                thumbnail_url=thumbnail_url["public_url"] if thumbnail_url else None,
                thumbnail_s3_key=thumbnail_url["s3_key"] if thumbnail_url else None,
                srt_s3_key=srt_url["s3_key"] if srt_url else None,
            )
            db.add(video)

            # 9. Update job as completed
            job.status = "completed"
            job.progress_pct = 100
            job.video_id = video.id
            job.draft_data = result["draft"]
            job.completed_at = datetime.now(timezone.utc)

            # 10. Track usage
            usage_service = UsageService(db)
            usage_service.increment_usage(job.user, cost_usd=job.cost_usd)

            db.commit()

            # 11. Optional: YouTube upload
            if job.auto_upload and job.channel_id:
                _upload_to_youtube(db, job, pipeline_job, video)

            # 12. Publish completion event
            _publish_progress(job_id, "completed", "done", 100)

        else:
            # Pipeline failed
            job.status = "failed"
            job.error_message = result.get("error", "Unknown error")
            db.commit()
            _publish_progress(job_id, "failed", "error", job.progress_pct)

    except SoftTimeLimitExceeded:
        job.status = "failed"
        job.error_message = "Job timed out (exceeded 9 minutes)"
        db.commit()
        _publish_progress(job_id, "timeout", "error", job.progress_pct)

    except Exception as e:
        logger.exception(f"Job {job_id} failed with exception")
        job.status = "failed"
        job.error_message = str(e)[:500]
        db.commit()
        _publish_progress(job_id, "error", "error", job.progress_pct)

        # Retry once on transient errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30)

    finally:
        db.close()
        # Clean up temp files
        if 'work_dir' in locals():
            shutil.rmtree(work_dir, ignore_errors=True)


def _update_job_progress(db, job, stage, status, pct, artifacts):
    """Update job record with stage progress."""
    from saas.models.job import JobStage
    from datetime import datetime, timezone

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
    """Publish progress event to Redis pub/sub for WebSocket delivery."""
    import json
    import redis

    r = redis.from_url("redis://localhost:6379/0")
    r.publish(f"job:{job_id}", json.dumps({
        "type": f"stage_{status}" if status in ("running", "done") else f"job_{status}",
        "stage": stage,
        "progress_pct": pct,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }))


def _upload_to_youtube(db, job, pipeline_job, video):
    """Upload completed video to user's YouTube channel."""
    from saas.utils.encryption import decrypt_value

    channel = db.query(YouTubeChannel).filter(
        YouTubeChannel.id == job.channel_id
    ).first()

    if not channel:
        return

    try:
        pipeline_job.config.youtube_access_token = decrypt_value(channel.access_token_enc)
        pipeline_job.config.youtube_refresh_token = decrypt_value(channel.refresh_token_enc) if channel.refresh_token_enc else ""

        youtube_url = pipeline_job.upload()

        video.youtube_url = youtube_url
        video.youtube_video_id = youtube_url.split("/")[-1]
        video.youtube_status = job.upload_privacy or "private"
        video.uploaded_to_youtube_at = datetime.now(timezone.utc)
        channel.last_upload_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        logger.error(f"YouTube upload failed for job {job.id}: {e}")
        # Don't fail the job — video is generated, just upload failed
```

---

## Periodic Tasks (Celery Beat)

```python
# saas/workers/celery_app.py — add to config

app.conf.beat_schedule = {
    # Refresh trending topics every 15 minutes
    "refresh-trending-topics": {
        "task": "saas.tasks.topic_task.refresh_trending_topics",
        "schedule": 900.0,  # 15 minutes
    },

    # Clean up expired media files every hour
    "cleanup-expired-media": {
        "task": "saas.tasks.cleanup_task.cleanup_expired_media",
        "schedule": 3600.0,  # 1 hour
    },

    # Sync usage with Stripe every 6 hours
    "sync-stripe-usage": {
        "task": "saas.tasks.billing_task.sync_usage_to_stripe",
        "schedule": 21600.0,  # 6 hours
    },

    # Process scheduled jobs every minute
    "process-scheduled-jobs": {
        "task": "saas.tasks.pipeline_task.process_scheduled_jobs",
        "schedule": 60.0,  # 1 minute
    },
}
```

```python
# saas/tasks/cleanup_task.py

@app.task
def cleanup_expired_media():
    """Delete S3 objects for expired videos (free tier: 7 days)."""
    from saas.models.video import Video
    from saas.services.storage_service import StorageService

    db = get_db_session()
    storage = StorageService()

    expired = db.query(Video).filter(
        Video.expires_at.isnot(None),
        Video.expires_at < datetime.now(timezone.utc),
    ).all()

    for video in expired:
        try:
            if video.video_s3_key:
                storage.delete_file(video.video_s3_key)
            if video.thumbnail_s3_key:
                storage.delete_file(video.thumbnail_s3_key)
            if video.srt_s3_key:
                storage.delete_file(video.srt_s3_key)

            video.video_url = None
            video.thumbnail_url = None
            logger.info(f"Cleaned up expired video {video.id}")
        except Exception as e:
            logger.error(f"Failed to clean up video {video.id}: {e}")

    db.commit()
    db.close()
```

```python
# saas/tasks/topic_task.py

@app.task
def refresh_trending_topics():
    """Refresh the global trending topics cache."""
    from pipeline.topics import TopicEngine
    from saas.models.topic import TrendingTopicCache

    db = get_db_session()
    engine = TopicEngine()
    candidates = engine.discover(limit=30)

    # Clear old entries
    db.query(TrendingTopicCache).filter(
        TrendingTopicCache.expires_at < datetime.now(timezone.utc)
    ).delete()

    # Insert fresh topics
    expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    for topic in candidates:
        db.add(TrendingTopicCache(
            source=topic.source,
            title=topic.title,
            summary=topic.summary,
            url=topic.url,
            trending_score=topic.trending_score,
            metadata=topic.metadata,
            expires_at=expires,
        ))

    db.commit()
    db.close()
    logger.info(f"Refreshed {len(candidates)} trending topics")
```

---

## SSE Progress Delivery

Job progress uses Server-Sent Events (SSE) instead of WebSocket. SSE is simpler
(unidirectional), has built-in browser auto-reconnect via `EventSource`, and works
through CDNs and reverse proxies without special configuration.

```python
# saas/api/v1/jobs.py — SSE endpoint

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
import redis.asyncio as aioredis
import json

@router.get("/jobs/{job_id}/events")
async def job_progress_sse(
    job_id: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SSE endpoint for real-time job progress updates."""
    # Verify user owns this job
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(404)

    async def event_stream():
        r = aioredis.from_url("redis://localhost:6379/0")
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
                    if event_type in ("job_completed", "job_failed"):
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
            "X-Accel-Buffering": "no",    # Disable nginx buffering
        },
    )
```

Client usage (auto-reconnects on network failure):
```typescript
const source = new EventSource(`/api/v1/jobs/${jobId}/events`)

source.addEventListener('stage_completed', (e) => {
  const data = JSON.parse(e.data)
  setProgress(data.progress_pct)
})

source.addEventListener('job_completed', (e) => {
  source.close()
})
```

---

## Job Scheduling

Users can schedule videos for future generation:

```python
# saas/tasks/pipeline_task.py

@app.task
def process_scheduled_jobs():
    """Check for scheduled jobs that are due and enqueue them."""
    db = get_db_session()

    due_jobs = db.query(Job).filter(
        Job.status == "queued",
        Job.scheduled_at.isnot(None),
        Job.scheduled_at <= datetime.now(timezone.utc),
    ).all()

    for job in due_jobs:
        # Determine queue based on user's plan
        queue = _get_queue_for_user(db, job.user_id)
        run_video_pipeline.apply_async(
            args=[str(job.id)],
            queue=queue,
        )
        logger.info(f"Enqueued scheduled job {job.id}")

    db.close()


def _get_queue_for_user(db, user_id: str) -> str:
    """Determine which Celery queue to use based on user's plan."""
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if sub and sub.plan.name in ("pro", "agency", "enterprise"):
        return "video_priority"
    return "video"
```

---

## Monitoring

### Celery Flower (Dashboard)

```bash
celery -A saas.workers.celery_app flower --port=5555
```

Provides:
- Worker status and concurrency
- Active/queued/completed task counts
- Task execution time histograms
- Failed task inspection

### Custom Metrics (Prometheus)

```python
# Track in each task
from prometheus_client import Counter, Histogram

jobs_completed = Counter("jobs_completed_total", "Total completed jobs", ["plan"])
jobs_failed = Counter("jobs_failed_total", "Total failed jobs", ["plan", "stage"])
job_duration = Histogram("job_duration_seconds", "Job execution time", ["plan"],
                         buckets=[30, 60, 120, 180, 300, 600])
stage_duration = Histogram("stage_duration_seconds", "Stage execution time", ["stage"],
                           buckets=[1, 5, 10, 30, 60, 120])
api_cost = Counter("api_cost_usd_total", "Total API cost in USD", ["provider"])
```
