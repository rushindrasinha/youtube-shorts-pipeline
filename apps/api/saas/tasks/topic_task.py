"""Periodic task to refresh trending topics cache."""

from datetime import datetime, timedelta, timezone

from celery.utils.log import get_task_logger
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SASession

from saas.workers.celery_app import app

logger = get_task_logger(__name__)


@app.task(bind=True, max_retries=2, soft_time_limit=120, time_limit=150)
def refresh_trending_topics(self):
    """Refresh global topic cache every 15 minutes.

    1. Clear expired topics from DB
    2. Fetch fresh topics from the TopicEngine
    3. Insert into TrendingTopicCache with 15 min expiry
    """
    from saas.settings import settings
    from saas.models.topic_cache import TrendingTopicCache

    engine = create_engine(settings.DATABASE_URL)
    db = SASession(engine)

    try:
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(minutes=15)

        # 1. Clear expired topics
        expired_count = (
            db.query(TrendingTopicCache)
            .filter(TrendingTopicCache.expires_at <= now)
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info(f"Cleared {expired_count} expired topics")

        # 2. Fetch fresh topics from TopicEngine
        try:
            from pipeline.topics import TopicEngine

            engine_instance = TopicEngine()
            raw_topics = engine_instance.fetch_trending()
        except ImportError:
            logger.warning(
                "pipeline.topics.TopicEngine not available, "
                "using empty topic list"
            )
            raw_topics = []
        except Exception as e:
            logger.error(f"Failed to fetch topics from TopicEngine: {e}")
            raw_topics = []

        # 3. Insert fresh topics into cache
        inserted = 0
        for topic in raw_topics:
            cache_entry = TrendingTopicCache(
                source=topic.get("source", "unknown"),
                title=topic.get("title", ""),
                summary=topic.get("summary"),
                url=topic.get("url"),
                trending_score=topic.get("trending_score", 0.0),
                extra_metadata=topic.get("metadata", {}),
                fetched_at=now,
                expires_at=expiry,
            )
            db.add(cache_entry)
            inserted += 1

        db.commit()
        logger.info(f"Inserted {inserted} fresh trending topics (expiry: {expiry})")

        return {"cleared": expired_count, "inserted": inserted}

    except Exception as e:
        logger.exception("Failed to refresh trending topics")
        db.rollback()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30)
        raise

    finally:
        db.close()
        engine.dispose()
