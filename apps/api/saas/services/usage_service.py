"""Basic usage tracking — full billing comes in Phase 2."""

from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.job import Job
from ..models.subscription import Plan, Subscription, UsageRecord


# Default limits when no subscription exists (free tier)
FREE_TIER_VIDEOS_PER_MONTH = 3


def check_can_create_job(db: Session, user) -> tuple[bool, str]:
    """Check whether the user can create a new job this billing period.

    Returns (allowed, reason_if_denied).
    """
    # Determine the user's video limit
    videos_limit = FREE_TIER_VIDEOS_PER_MONTH
    if user.subscription and user.subscription.plan:
        videos_limit = user.subscription.plan.videos_per_month

    # Count jobs created this calendar month
    now = datetime.now(timezone.utc)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    jobs_this_month = (
        db.query(Job)
        .filter(
            Job.user_id == user.id,
            Job.created_at >= period_start,
            Job.status != "canceled",
        )
        .count()
    )

    if jobs_this_month >= videos_limit:
        return False, (
            f"You have used all {videos_limit} videos for this billing period. "
            f"Upgrade your plan or wait until next month."
        )

    return True, ""


def increment_usage(db: Session, user, cost_usd: float = 0.0) -> None:
    """Increment the user's monthly usage counter."""
    now = datetime.now(timezone.utc)
    period_start = now.replace(day=1).date()

    # Determine end of month
    if now.month == 12:
        period_end = date(now.year + 1, 1, 1)
    else:
        period_end = date(now.year, now.month + 1, 1)

    # Determine limit
    videos_limit = FREE_TIER_VIDEOS_PER_MONTH
    if user.subscription and user.subscription.plan:
        videos_limit = user.subscription.plan.videos_per_month

    # Upsert usage record
    usage = (
        db.query(UsageRecord)
        .filter(
            UsageRecord.user_id == user.id,
            UsageRecord.period_start == period_start,
        )
        .first()
    )

    if not usage:
        usage = UsageRecord(
            user_id=user.id,
            period_start=period_start,
            period_end=period_end,
            videos_limit=videos_limit,
            videos_created=0,
        )
        db.add(usage)

    usage.videos_created += 1
    usage.total_api_cost += cost_usd
    db.commit()
