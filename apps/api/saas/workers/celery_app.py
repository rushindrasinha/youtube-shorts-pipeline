from celery import Celery
from celery.signals import worker_init
from saas.settings import settings

app = Celery("shortfactory")

_redis_base = settings.REDIS_URL.rstrip("/0").rstrip("/")

app.config_from_object({
    "broker_url": settings.REDIS_URL,
    "result_backend": f"{_redis_base}/1",
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
    "worker_concurrency": 2,
    "task_time_limit": 900,          # 15 min hard limit
    "task_soft_time_limit": 840,     # 14 min soft limit

    # Retry configuration
    "task_acks_late": True,
    "worker_prefetch_multiplier": 1,
    "task_reject_on_worker_lost": True,

    # Result expiry
    "result_expires": 86400,         # 24 hours

    # Connection settings
    "broker_connection_retry_on_startup": False,
    "broker_connection_retry": False,
    "redis_retry_on_timeout": False,
    "result_backend_transport_options": {
        "retry_on_timeout": False,
        "max_retries": 0,
    },
})


app.conf.beat_schedule = {
    "refresh-trending-topics": {
        "task": "saas.tasks.topic_task.refresh_trending_topics",
        "schedule": 900.0,  # Every 15 minutes
    },
    "cleanup-expired-media": {
        "task": "saas.tasks.cleanup_task.cleanup_expired_media",
        "schedule": 3600.0 * 24,  # Daily
    },
    "process-scheduled-jobs": {
        "task": "saas.tasks.scheduler_task.process_scheduled_jobs",
        "schedule": 60.0,  # Every minute
    },
}


@worker_init.connect
def init_worker(**kwargs):
    """Called when a Celery worker starts."""
    print("Worker initialized.")
