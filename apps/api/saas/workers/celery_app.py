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
    "worker_concurrency": 2,
    "task_time_limit": 900,          # 15 min hard limit
    "task_soft_time_limit": 840,     # 14 min soft limit

    # Retry configuration
    "task_acks_late": True,
    "worker_prefetch_multiplier": 1,
    "task_reject_on_worker_lost": True,

    # Result expiry
    "result_expires": 86400,         # 24 hours
})


@worker_init.connect
def init_worker(**kwargs):
    """Called when a Celery worker starts.

    NOTE: Whisper model is NOT pre-loaded here. It is cached at module level
    in pipeline/captions.py (_get_whisper_model). Loading in two places wastes
    memory and creates confusion about which global is used. The captions module
    cache is the single source of truth.
    """
    print("Worker initialized.")
