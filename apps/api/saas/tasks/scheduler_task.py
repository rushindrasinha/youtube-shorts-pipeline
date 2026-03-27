from datetime import datetime, timezone
from saas.workers.celery_app import app

@app.task
def process_scheduled_jobs():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from saas.settings import settings
    from saas.models.job import Job
    engine = create_engine(settings.DATABASE_URL)
    db = Session(engine)
    try:
        due = db.query(Job).filter(Job.status == "queued", Job.scheduled_at.isnot(None), Job.scheduled_at <= datetime.now(timezone.utc)).all()
        for job in due:
            from saas.tasks.pipeline_task import run_video_pipeline
            run_video_pipeline.delay(str(job.id))
    finally:
        db.close()
        engine.dispose()
