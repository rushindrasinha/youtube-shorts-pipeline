"""Tests for the Celery pipeline task."""

import sys
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock
from uuid import UUID

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
    import sqlite3
    from uuid import UUID as PyUUID
    from sqlalchemy.dialects.postgresql import ARRAY
    from sqlalchemy.ext.compiler import compiles
    from sqlalchemy import Uuid
    from sqlalchemy.pool import StaticPool

    @compiles(ARRAY, "sqlite")
    def _compile_array_sqlite(type_, compiler, **kw):
        return "TEXT"

    sqlite3.register_adapter(PyUUID, lambda u: str(u))

    def _patched_bind_processor(self, dialect):
        def process(value):
            if value is None:
                return value
            if isinstance(value, str):
                try:
                    value = PyUUID(value)
                except ValueError:
                    return value
            if hasattr(value, 'hex'):
                return value.hex
            return str(value)
        return process

    Uuid.bind_processor = _patched_bind_processor

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

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

    for stage_name in ["research", "draft", "broll", "voiceover", "captions", "music", "assemble", "thumbnail"]:
        stage = JobStage(job_id=job.id, stage_name=stage_name, status="pending")
        db.add(stage)

    db.commit()
    db.refresh(job)
    return user, job


class _NonClosingSession:
    """Wraps a session but makes close() a no-op so tests can verify state."""

    def __init__(self, session):
        self._session = session

    def close(self):
        pass  # Don't actually close -- test needs to read data after

    def __getattr__(self, name):
        return getattr(self._session, name)


def _run_task(db, engine, job_id, pipeline_behavior):
    """Run the pipeline task with mocked dependencies.

    pipeline_behavior: either a dict (return value) or an exception (side effect).
    """
    mock_redis_client = MagicMock()
    mock_redis_client.close = MagicMock()

    mock_pipeline_instance = MagicMock()
    if isinstance(pipeline_behavior, Exception):
        mock_pipeline_instance.run.side_effect = pipeline_behavior
    else:
        mock_pipeline_instance.run.return_value = pipeline_behavior

    # Wrap session so close() is a no-op
    wrapped_db = _NonClosingSession(db)

    # Wrap engine so dispose() is a no-op (test needs the connection alive)
    mock_engine = MagicMock(wraps=engine)
    mock_engine.dispose = MagicMock()  # no-op

    with patch("saas.tasks.pipeline_task.create_engine", return_value=mock_engine), \
         patch("saas.tasks.pipeline_task.SASession", return_value=wrapped_db), \
         patch("saas.tasks.pipeline_task.redis") as mock_redis_mod, \
         patch("saas.tasks.pipeline_task.resolve_api_keys") as mock_keys, \
         patch("pipeline.adapter.PipelineJob", return_value=mock_pipeline_instance):

        mock_redis_mod.from_url.return_value = mock_redis_client
        mock_keys.return_value = {
            "anthropic": "test-key",
            "gemini": "test-key",
            "elevenlabs": "test-key",
        }

        from saas.tasks.pipeline_task import run_video_pipeline

        run_video_pipeline.push_request(
            id="test-celery-task-id",
            retries=1,
        )
        try:
            run_video_pipeline.run(str(job_id))
        finally:
            run_video_pipeline.pop_request()

    return mock_redis_client, mock_pipeline_instance


class TestPipelineTaskUpdatesProgress:
    def test_pipeline_task_updates_progress(self, engine, db):
        """Mock PipelineJob to succeed, verify DB updates and Redis publish."""
        user, job = _create_user_and_job(db)

        mock_redis, mock_pipeline = _run_task(
            db, engine, job.id,
            pipeline_behavior={
                "status": "completed",
                "job_id": str(job.id),
                "draft": {"script": "Test script", "youtube_title": "Test"},
                "video_path": "/tmp/test.mp4",
                "thumbnail_path": "/tmp/thumb.png",
                "srt_path": "/tmp/captions.srt",
            },
        )

        # Verify job was updated in DB
        db.expire_all()
        job = db.query(Job).filter(Job.id == job.id).first()
        assert job.status == "completed"
        assert job.progress_pct == 100
        assert job.completed_at is not None

        # Verify Redis publish was called (for SSE delivery)
        assert mock_redis.publish.called

        # Verify PipelineJob.run() was called
        assert mock_pipeline.run.called


class TestPipelineTaskHandlesFailure:
    def test_pipeline_task_handles_failure(self, engine, db):
        """Mock PipelineJob to raise exception, verify error stored."""
        user, job = _create_user_and_job(db)

        mock_redis, _ = _run_task(
            db, engine, job.id,
            pipeline_behavior=RuntimeError("ElevenLabs API rate limited"),
        )

        # Verify job was marked as failed
        db.expire_all()
        job = db.query(Job).filter(Job.id == job.id).first()
        assert job.status == "failed"
        assert "ElevenLabs API rate limited" in job.error_message
        assert job.completed_at is not None

    def test_pipeline_task_pipeline_returns_failed(self, engine, db):
        """Pipeline returns failed status (graceful failure, not exception)."""
        user, job = _create_user_and_job(db)

        mock_redis, _ = _run_task(
            db, engine, job.id,
            pipeline_behavior={
                "status": "failed",
                "error": "Gemini image generation failed",
            },
        )

        db.expire_all()
        job = db.query(Job).filter(Job.id == job.id).first()
        assert job.status == "failed"
        assert "Gemini image generation failed" in job.error_message
