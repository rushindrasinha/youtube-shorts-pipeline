"""Periodic task to delete expired media (free tier 7-day expiry)."""

from datetime import datetime, timezone

from celery.utils.log import get_task_logger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession

from saas.workers.celery_app import app

logger = get_task_logger(__name__)

BATCH_SIZE = 100


@app.task(name="saas.tasks.cleanup_task.cleanup_expired_media")
def cleanup_expired_media():
    """Batch delete expired videos from S3.

    Queries in batches of 100 to avoid loading all expired records into memory.
    Deletes S3 files and clears URL/key fields in the Video record.
    """
    from saas.settings import settings
    from saas.models.video import Video
    from saas.services.storage_service import StorageService

    engine = create_engine(settings.DATABASE_URL)
    db = SASession(engine)
    storage = StorageService()

    try:
        now = datetime.now(timezone.utc)
        total_cleaned = 0

        while True:
            # Query batch of expired videos that still have S3 keys
            expired_videos = (
                db.query(Video)
                .filter(
                    Video.expires_at.isnot(None),
                    Video.expires_at <= now,
                    Video.video_s3_key.isnot(None),
                    Video.video_s3_key != "",
                )
                .limit(BATCH_SIZE)
                .all()
            )

            if not expired_videos:
                break

            for video in expired_videos:
                # Delete S3 files
                try:
                    if video.video_s3_key:
                        storage.delete_file(video.video_s3_key)
                    if video.thumbnail_s3_key:
                        storage.delete_file(video.thumbnail_s3_key)
                    if video.srt_s3_key:
                        storage.delete_file(video.srt_s3_key)
                except Exception as e:
                    logger.warning(
                        f"Failed to delete S3 files for video {video.id}: {e}"
                    )

                # Clear URLs and S3 keys in the record (keep the record for history)
                video.video_s3_key = ""
                video.video_url = ""
                video.thumbnail_s3_key = None
                video.thumbnail_url = None
                video.srt_s3_key = None

                total_cleaned += 1

            db.commit()
            logger.info(f"Cleaned up batch of {len(expired_videos)} expired videos")

        logger.info(f"Cleanup complete: {total_cleaned} expired videos processed")

    except Exception:
        logger.exception("Error during expired media cleanup")
        db.rollback()
    finally:
        db.close()
        engine.dispose()
