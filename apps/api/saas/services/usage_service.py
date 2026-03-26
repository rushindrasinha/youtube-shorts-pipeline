"""Usage tracking with plan limit checking and overage billing."""

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.job import Job
from ..models.subscription import Plan, Subscription, UsageRecord


# Default limits when no subscription exists (free tier)
FREE_TIER_VIDEOS_PER_MONTH = 3


def check_can_create_job(db: Session, user) -> tuple[bool, str]:
    """Check whether the user can create a new job this billing period.

    Returns (allowed, reason_if_denied).
    For paid tiers with overage_cents > 0, overage is allowed.
    For free tier, it's a hard limit.
    """
    sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id)
        .first()
    )

    plan = None
    videos_limit = FREE_TIER_VIDEOS_PER_MONTH

    if sub and sub.plan:
        plan = sub.plan
        videos_limit = plan.videos_per_month

    # Unlimited plans
    if videos_limit == -1:
        return True, ""

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
        # Check if plan supports overage (paid tiers)
        if plan and plan.overage_cents > 0:
            return True, "overage"
        return False, (
            f"You have used all {videos_limit} videos for this billing period. "
            f"Upgrade your plan or wait until next month."
        )

    return True, ""


def increment_usage(db: Session, user, cost_usd: float = 0.0) -> None:
    """Increment the user's monthly usage counter.

    Tracks overage and reports to Stripe for metered billing on paid plans.
    """
    now = datetime.now(timezone.utc)
    period_start = now.replace(day=1).date()

    # Determine end of month
    if now.month == 12:
        period_end = date(now.year + 1, 1, 1)
    else:
        period_end = date(now.year, now.month + 1, 1)

    # Determine limit from plan
    videos_limit = FREE_TIER_VIDEOS_PER_MONTH
    plan = None
    if user.subscription and user.subscription.plan:
        plan = user.subscription.plan
        videos_limit = plan.videos_per_month

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

    # Track overage and report to Stripe for metered billing
    if (
        plan
        and plan.overage_cents > 0
        and videos_limit > 0
        and usage.videos_created > videos_limit
    ):
        usage.overage_count += 1

        # Report metered usage to Stripe
        from .billing_service import BillingService

        try:
            BillingService(db).record_usage(user, quantity=1)
        except Exception:
            pass  # Don't fail the job if Stripe reporting fails

    db.commit()
