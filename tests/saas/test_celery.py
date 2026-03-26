"""Tests for the Celery pipeline task."""

import sys
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

# Add apps/api to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "api"))

from saas.models import Base
from saas.models.job import Job, JobStage
from saas.models.user import User
from saas.models.subscription import Plan, Subscription
from saas.services.auth_service import hash_password


@pytest.fixture(scope="function")
def engine():
    """In-memory SQLite engine for testing."""
    from sqlalchemy.dialects.postgresql import ARRAY
    from sqlalchemy.ext.compiler import compiles

    @compiles(ARRAY, "sqlite")
    def _compile_array_sqlite(type_, compiler, **kw):
        return "TEXT"

    eng = create_engine("sqlite:///:memory:")

    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    partial_indexes = []
    for table in Base.metadata.tables.values():
        to_remove = []
        for idx in table.indexes:
            dialect_opts = idx.dialect_options.get("postgresql", {})
            if dialect_opts.get("where") is not None:
                to_remove.append(idx)
        for idx in to_remove:
            table.indexes.discard(idx)
            partial_indexes.append((table, idx))

    Base.metadata.create_all(eng)

    for table, idx in partial_indexes:
        table.indexes.add(idx)

    yield eng

    with eng.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.commit()
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture(scope="function")
def db(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _create_user_and_job(db):
    """Create a test user with free plan and a queued job."""
    plan = Plan(
        name="free",
        display_name="Free",
        videos_per_month=3,
        channels_limit=1,
        team_seats=1,
        price_cents=0,
        overage_cents=0,
        features={},
    )
    db.add(plan)
    db.flush()

    user = User(
        email="worker@example.com",
        password_hash=hash_password("testpassword"),
        display_name="Worker Test",
    )
    db.add(user)
    db.flush()

    sub = Subscription(user_id=user.id, plan_id=plan.id, status="active")
    db.add(sub)
    db.flush()

    job = Job(
        user_id=user.id,
        topic="Test pipeline topic",
        status="queued",
        progress_pct=0,
    )
    db.add(job)
    db.flush()

    # Create initial stages
    for stage_name in ["research", "draft", "broll", "voiceover", "captions", "music", "assemble", "thumbnail"]:
        stage = JobStage(job_id=job.id, stage_name=stage_name, status="pending")
        db.add(stage)

    db.commit()
    db.refresh(job)
    return user, job


class TestPipelineTaskUpdatesProgress:
    @patch("saas.tasks.pipeline_task.redis")
    @patch("saas.tasks.pipeline_task.create_engine")
    def test_pipeline_task_updates_progress(self, mock_create_engine, mock_redis_mod, engine, db):
        """Mock PipelineJob, verify DB updates and Redis publish."""
        user, job = _create_user_and_job(db)

        # Make create_engine return our test engine
        mock_create_engine.return_value = engine

        # Mock SASession to return our test session
        mock_redis_client = MagicMock()
        mock_redis_mod.from_url.return_value = mock_redis_client

        # Mock PipelineJob.run() to return success and call the progress callback
        with patch("saas.tasks.pipeline_task.PipelineJob") as MockPipeline, \
             patch("saas.tasks.pipeline_task.SASession") as MockSession, \
             patch("saas.tasks.pipeline_task.resolve_api_keys") as mock_keys:

            mock_keys.return_value = {
                "anthropic": "test-key",
                "gemini": "test-key",
                "elevenlabs": "test-key",
            }

            # The session mock returns our db session
            MockSession.return_value = db

            def mock_run():
                return {
                    "status": "completed",
                    "job_id": str(job.id),
                    "draft": {"script": "Test script", "youtube_title": "Test"},
                    "video_path": "/tmp/test.mp4",
                    "thumbnail_path": "/tmp/thumb.png",
                    "srt_path": "/tmp/captions.srt",
                }

            mock_pipeline_instance = MagicMock()
            mock_pipeline_instance.run.side_effect = mock_run
            MockPipeline.return_value = mock_pipeline_instance

            # Import and call the task function directly (not via Celery)
            from saas.tasks.pipeline_task import run_video_pipeline

            # Create a mock self (Celery task context)
            mock_self = MagicMock()
            mock_self.request.id = "test-celery-task-id"
            mock_self.request.retries = 0
            mock_self.max_retries = 1

            # Call the underlying function directly
            run_video_pipeline.__wrapped__(mock_self, str(job.id))

            # Verify job was updated
            db.refresh(job)
            assert job.status == "completed"
            assert job.progress_pct == 100
            assert job.completed_at is not None

            # Verify Redis publish was called
            assert mock_redis_client.publish.called


class TestPipelineTaskHandlesFailure:
    @patch("saas.tasks.pipeline_task.redis")
    @patch("saas.tasks.pipeline_task.create_engine")
    def test_pipeline_task_handles_failure(self, mock_create_engine, mock_redis_mod, engine, db):
        """Mock PipelineJob to raise, verify error is stored."""
        user, job = _create_user_and_job(db)

        mock_create_engine.return_value = engine

        mock_redis_client = MagicMock()
        mock_redis_mod.from_url.return_value = mock_redis_client

        with patch("saas.tasks.pipeline_task.PipelineJob") as MockPipeline, \
             patch("saas.tasks.pipeline_task.SASession") as MockSession, \
             patch("saas.tasks.pipeline_task.resolve_api_keys") as mock_keys:

            mock_keys.return_value = {
                "anthropic": "test-key",
                "gemini": "test-key",
                "elevenlabs": "test-key",
            }

            MockSession.return_value = db

            # Pipeline raises an exception
            mock_pipeline_instance = MagicMock()
            mock_pipeline_instance.run.side_effect = RuntimeError("ElevenLabs API rate limited")
            MockPipeline.return_value = mock_pipeline_instance

            from saas.tasks.pipeline_task import run_video_pipeline

            mock_self = MagicMock()
            mock_self.request.id = "test-celery-task-id"
            mock_self.request.retries = 1  # Already retried once
            mock_self.max_retries = 1

            # Should not raise (retries exhausted)
            run_video_pipeline.__wrapped__(mock_self, str(job.id))

            # Verify job was marked as failed
            db.refresh(job)
            assert job.status == "failed"
            assert "ElevenLabs API rate limited" in job.error_message
            assert job.completed_at is not None

    @patch("saas.tasks.pipeline_task.redis")
    @patch("saas.tasks.pipeline_task.create_engine")
    def test_pipeline_task_pipeline_returns_failed(self, mock_create_engine, mock_redis_mod, engine, db):
        """Pipeline returns failed status (not an exception)."""
        user, job = _create_user_and_job(db)

        mock_create_engine.return_value = engine

        mock_redis_client = MagicMock()
        mock_redis_mod.from_url.return_value = mock_redis_client

        with patch("saas.tasks.pipeline_task.PipelineJob") as MockPipeline, \
             patch("saas.tasks.pipeline_task.SASession") as MockSession, \
             patch("saas.tasks.pipeline_task.resolve_api_keys") as mock_keys:

            mock_keys.return_value = {
                "anthropic": "test-key",
                "gemini": "test-key",
                "elevenlabs": "test-key",
            }

            MockSession.return_value = db

            mock_pipeline_instance = MagicMock()
            mock_pipeline_instance.run.return_value = {
                "status": "failed",
                "error": "Gemini image generation failed",
            }
            MockPipeline.return_value = mock_pipeline_instance

            from saas.tasks.pipeline_task import run_video_pipeline

            mock_self = MagicMock()
            mock_self.request.id = "test-celery-task-id"
            mock_self.request.retries = 0
            mock_self.max_retries = 1

            run_video_pipeline.__wrapped__(mock_self, str(job.id))

            db.refresh(job)
            assert job.status == "failed"
            assert "Gemini image generation failed" in job.error_message
