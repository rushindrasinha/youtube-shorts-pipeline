"""Stripe billing service — checkout, portal, metered usage."""

from datetime import datetime, timezone

import stripe
from sqlalchemy.orm import Session

from ..models.subscription import Plan, Subscription
from ..models.user import User
from ..settings import settings


class BillingService:
    def __init__(self, db: Session):
        self.db = db
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def create_checkout_session(self, user: User, plan_name: str) -> str:
        """Create a Stripe Checkout session for plan subscription.

        Returns the checkout URL.
        """
        plan = self.db.query(Plan).filter(Plan.name == plan_name).first()
        if not plan or not plan.stripe_price_id:
            raise ValueError(f"Invalid plan: {plan_name}")

        # Ensure Stripe customer exists
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.display_name,
                metadata={"user_id": str(user.id)},
            )
            user.stripe_customer_id = customer.id
            self.db.commit()

        session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            mode="subscription",
            line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
            success_url=f"{settings.FRONTEND_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/billing/canceled",
            metadata={"user_id": str(user.id), "plan": plan_name},
            subscription_data={
                "metadata": {"user_id": str(user.id), "plan": plan_name},
            },
        )
        return session.url

    def create_portal_session(self, user: User) -> str:
        """Create Stripe Customer Portal session for self-service billing management.

        Returns the portal URL.
        """
        if not user.stripe_customer_id:
            raise ValueError("User has no Stripe customer record")

        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL}/billing",
        )
        return session.url

    def record_usage(self, user: User, quantity: int = 1):
        """Report metered usage for overage billing."""
        sub = (
            self.db.query(Subscription)
            .filter(Subscription.user_id == user.id)
            .first()
        )
        if not sub or not sub.stripe_subscription_id:
            return

        # Find metered subscription item
        stripe_sub = stripe.Subscription.retrieve(sub.stripe_subscription_id)
        for item in stripe_sub["items"]["data"]:
            price = item["price"]
            if price.get("recurring", {}).get("usage_type") == "metered":
                stripe.SubscriptionItem.create_usage_record(
                    item["id"],
                    quantity=quantity,
                    timestamp=int(datetime.now(timezone.utc).timestamp()),
                )
                break
