import sys
import os
from datetime import datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError

# Add apps/api to path so saas package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "api"))

from saas.models import (
    User,
    Job,
    JobStage,
    Team,
    Plan,
    Video,
)


def test_user_creation(session):
    """Create a user, verify UUIDv7 PK and timestamps are set."""
    user = User(email="test@example.com", display_name="Test User")
    session.add(user)
    session.commit()

    assert user.id is not None
    assert isinstance(user.id, UUID)
    assert user.email == "test@example.com"
    assert user.display_name == "Test User"
    assert user.created_at is not None
    assert isinstance(user.created_at, datetime)
    assert user.updated_at is not None
    assert user.is_active is True
    assert user.role == "user"


def test_job_stages_cascade(session):
    """Create a job with stages, delete the job, verify stages are cascade deleted."""
    user = User(email="cascade@example.com")
    session.add(user)
    session.flush()

    job = Job(user_id=user.id, topic="Test topic")
    session.add(job)
    session.flush()

    stage1 = JobStage(job_id=job.id, stage_name="research", status="done")
    stage2 = JobStage(job_id=job.id, stage_name="draft", status="pending")
    session.add_all([stage1, stage2])
    session.commit()

    # Verify stages exist
    assert session.query(JobStage).filter_by(job_id=job.id).count() == 2

    # Delete the job
    session.delete(job)
    session.commit()

    # Verify stages are gone (cascade delete)
    assert session.query(JobStage).count() == 0


def test_team_owner_restrict(session):
    """Deleting a user who owns a team should raise IntegrityError (RESTRICT).

    Note: SQLite does not support ON DELETE RESTRICT distinctly from NO ACTION,
    but with foreign_keys=ON it will raise IntegrityError when trying to delete
    a user referenced by teams.owner_id.
    """
    user = User(email="owner@example.com")
    session.add(user)
    session.flush()

    team = Team(name="My Team", slug="my-team", owner_id=user.id)
    session.add(team)
    session.commit()

    # Attempting to delete the owner should fail
    session.delete(user)
    with pytest.raises(IntegrityError):
        session.commit()

    session.rollback()

    # Verify user still exists
    assert session.query(User).filter_by(email="owner@example.com").one() is not None


def test_plan_seed_data(session):
    """Verify Plan model can be instantiated with all required fields."""
    plan = Plan(
        name="pro",
        display_name="Pro",
        videos_per_month=100,
        channels_limit=10,
        team_seats=3,
        price_cents=4900,
        overage_cents=60,
        features={
            "caption_styles": True,
            "byok": True,
            "trending_topics": True,
            "priority_queue": True,
        },
    )
    session.add(plan)
    session.commit()

    assert plan.id is not None
    assert isinstance(plan.id, UUID)
    assert plan.name == "pro"
    assert plan.display_name == "Pro"
    assert plan.videos_per_month == 100
    assert plan.channels_limit == 10
    assert plan.team_seats == 3
    assert plan.price_cents == 4900
    assert plan.overage_cents == 60
    assert plan.features["priority_queue"] is True
    assert plan.is_active is True
    assert plan.created_at is not None
