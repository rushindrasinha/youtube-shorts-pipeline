"""Billing API endpoints — plans, subscription, checkout, portal."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...models.subscription import Plan, Subscription
from ...models.user import User
from ...schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    PlanResponse,
    PlansListResponse,
    PortalResponse,
    SubscriptionResponse,
)
from ...schemas.common import ErrorDetail, ErrorResponse
from ...services.billing_service import BillingService
from ..deps import get_current_user, get_db

router = APIRouter()


@router.get("/plans", response_model=PlansListResponse)
async def list_plans(db: Session = Depends(get_db)):
    """List all active plans."""
    plans = (
        db.query(Plan)
        .filter(Plan.is_active == True)  # noqa: E712
        .order_by(Plan.sort_order)
        .all()
    )
    return PlansListResponse(
        plans=[PlanResponse.model_validate(p) for p in plans]
    )


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's subscription."""
    sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id)
        .first()
    )
    if not sub:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="NOT_FOUND", message="No subscription found"
                )
            ).model_dump(),
        )

    return SubscriptionResponse(
        plan=PlanResponse.model_validate(sub.plan),
        status=sub.status,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
    )


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for plan subscription."""
    billing = BillingService(db)
    try:
        url = billing.create_checkout_session(user, body.plan)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_INPUT", message=str(e)
                )
            ).model_dump(),
        )
    return CheckoutResponse(checkout_url=url)


@router.post("/portal", response_model=PortalResponse)
async def create_portal(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Customer Portal session for self-service management."""
    billing = BillingService(db)
    try:
        url = billing.create_portal_session(user)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_INPUT", message=str(e)
                )
            ).model_dump(),
        )
    return PortalResponse(portal_url=url)


@router.get("/billing/invoices")
def list_invoices(user=Depends(get_current_user)):
    import stripe as _stripe
    from ...settings import settings
    _stripe.api_key = settings.STRIPE_SECRET_KEY
    if not user.stripe_customer_id:
        return {"invoices": []}
    try:
        invoices = _stripe.Invoice.list(customer=user.stripe_customer_id, limit=20)
        return {"invoices": [{"id": i.id, "amount_cents": i.total, "status": i.status, "date": i.created} for i in invoices.data]}
    except Exception:
        return {"invoices": []}
