"""Stripe webhook handler — unauthenticated, verifies signature."""

from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ...models.subscription import Plan, Subscription, UsageRecord
from ...models.user import User
from ...settings import settings
from ..deps import get_db

router = APIRouter()


@router.post("/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events.

    This endpoint is UNAUTHENTICATED but verifies the Stripe signature.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "customer.subscription.created":
        _handle_subscription_created(db, data)

    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(db, data)

    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(db, data)

    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(db, data)

    return {"status": "ok"}


def _handle_subscription_created(db: Session, stripe_sub: dict):
    """Activate subscription when Stripe confirms creation."""
    user_id = stripe_sub.get("metadata", {}).get("user_id")
    plan_name = stripe_sub.get("metadata", {}).get("plan")

    if not user_id or not plan_name:
        return

    user = db.query(User).filter(User.id == user_id).first()
    plan = db.query(Plan).filter(Plan.name == plan_name).first()

    if not user or not plan:
        return

    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if sub:
        sub.plan_id = plan.id
        sub.stripe_subscription_id = stripe_sub["id"]
        sub.status = stripe_sub.get("status", "active")
        sub.current_period_start = datetime.fromtimestamp(
            stripe_sub["current_period_start"], tz=timezone.utc
        )
        sub.current_period_end = datetime.fromtimestamp(
            stripe_sub["current_period_end"], tz=timezone.utc
        )
    else:
        sub = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            stripe_subscription_id=stripe_sub["id"],
            status=stripe_sub.get("status", "active"),
            current_period_start=datetime.fromtimestamp(
                stripe_sub["current_period_start"], tz=timezone.utc
            ),
            current_period_end=datetime.fromtimestamp(
                stripe_sub["current_period_end"], tz=timezone.utc
            ),
        )
        db.add(sub)

    # Ensure a usage record exists for this period
    _ensure_usage_record(db, user, plan)
    db.commit()


def _handle_subscription_updated(db: Session, stripe_sub: dict):
    """Update subscription when plan changes or status changes."""
    sub = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id == stripe_sub["id"])
        .first()
    )
    if not sub:
        return

    # Check if plan changed via metadata
    plan_name = stripe_sub.get("metadata", {}).get("plan")
    if plan_name:
        plan = db.query(Plan).filter(Plan.name == plan_name).first()
        if plan:
            sub.plan_id = plan.id

    sub.status = stripe_sub.get("status", sub.status)
    sub.cancel_at_period_end = stripe_sub.get("cancel_at_period_end", False)

    if "current_period_start" in stripe_sub:
        sub.current_period_start = datetime.fromtimestamp(
            stripe_sub["current_period_start"], tz=timezone.utc
        )
    if "current_period_end" in stripe_sub:
        sub.current_period_end = datetime.fromtimestamp(
            stripe_sub["current_period_end"], tz=timezone.utc
        )

    db.commit()


def _handle_subscription_deleted(db: Session, stripe_sub: dict):
    """Downgrade to free when subscription is canceled."""
    free_plan = db.query(Plan).filter(Plan.name == "free").first()
    sub = (
        db.query(Subscription)
        .filter(Subscription.stripe_subscription_id == stripe_sub["id"])
        .first()
    )

    if sub and free_plan:
        sub.plan_id = free_plan.id
        sub.status = "canceled"
        sub.stripe_subscription_id = None
        sub.cancel_at_period_end = False
        db.commit()


def _handle_payment_failed(db: Session, invoice: dict):
    """Handle failed payment -- set subscription to past_due."""
    customer_id = invoice.get("customer")
    if not customer_id:
        return

    user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
    if not user:
        return

    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if sub:
        sub.status = "past_due"
        db.commit()


def _ensure_usage_record(db: Session, user: User, plan: Plan):
    """Create a usage record for the current billing period if one doesn't exist."""
    now = datetime.now(timezone.utc)
    period_start = now.replace(day=1).date()

    existing = (
        db.query(UsageRecord)
        .filter(
            UsageRecord.user_id == user.id,
            UsageRecord.period_start == period_start,
        )
        .first()
    )

    if not existing:
        from datetime import date, timedelta

        if now.month == 12:
            period_end = date(now.year + 1, 1, 1) - timedelta(days=1)
        else:
            period_end = date(now.year, now.month + 1, 1) - timedelta(days=1)

        usage = UsageRecord(
            user_id=user.id,
            period_start=period_start,
            period_end=period_end,
            videos_limit=plan.videos_per_month,
        )
        db.add(usage)
