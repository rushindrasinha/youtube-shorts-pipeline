"""Tests for Billing API endpoints."""

import sys
import os
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "api"))

from saas.models.subscription import Plan
from tests.saas.conftest import create_test_user


def _auth_headers(db_session, email="billing-test@example.com", user=None):
    """Create auth headers with a valid JWT for the given user."""
    from saas.services.auth_service import create_access_token

    if user is None:
        user = create_test_user(db_session, email=email)
    token = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}, user


def _seed_all_plans(db_session):
    """Seed the 5 standard plans into the database."""
    plans_data = [
        {
            "name": "free",
            "display_name": "Free",
            "price_cents": 0,
            "videos_per_month": 3,
            "channels_limit": 1,
            "team_seats": 1,
            "features": {"caption_styles": False, "byok": False, "trending_topics": False},
            "overage_cents": 0,
            "sort_order": 0,
        },
        {
            "name": "creator",
            "display_name": "Creator",
            "price_cents": 1900,
            "videos_per_month": 30,
            "channels_limit": 3,
            "team_seats": 1,
            "features": {"caption_styles": True, "byok": True, "trending_topics": True},
            "overage_cents": 75,
            "stripe_price_id": "price_creator_test",
            "sort_order": 1,
        },
        {
            "name": "pro",
            "display_name": "Pro",
            "price_cents": 4900,
            "videos_per_month": 100,
            "channels_limit": 10,
            "team_seats": 5,
            "features": {"caption_styles": True, "byok": True, "trending_topics": True},
            "overage_cents": 60,
            "stripe_price_id": "price_pro_test",
            "sort_order": 2,
        },
        {
            "name": "agency",
            "display_name": "Agency",
            "price_cents": 14900,
            "videos_per_month": 500,
            "channels_limit": 50,
            "team_seats": 25,
            "features": {"caption_styles": True, "byok": True, "trending_topics": True},
            "overage_cents": 40,
            "stripe_price_id": "price_agency_test",
            "sort_order": 3,
        },
        {
            "name": "enterprise",
            "display_name": "Enterprise",
            "price_cents": 0,
            "videos_per_month": -1,
            "channels_limit": -1,
            "team_seats": -1,
            "features": {"caption_styles": True, "byok": True, "trending_topics": True},
            "overage_cents": 0,
            "sort_order": 4,
        },
    ]

    # Remove existing free plan to avoid duplicates (conftest seeds one)
    existing_free = db_session.query(Plan).filter(Plan.name == "free").first()
    if existing_free:
        db_session.delete(existing_free)
        db_session.flush()

    for pd in plans_data:
        plan = Plan(**pd)
        db_session.add(plan)
    db_session.commit()


class TestListPlans:
    def test_list_plans(self, client, db_session):
        """GET /billing/plans returns all active plans."""
        _seed_all_plans(db_session)

        response = client.get("/api/v1/billing/plans")
        assert response.status_code == 200
        data = response.json()
        assert "plans" in data
        assert len(data["plans"]) == 5

        # Verify order
        names = [p["name"] for p in data["plans"]]
        assert names == ["free", "creator", "pro", "agency", "enterprise"]

    def test_list_plans_unauthenticated(self, client, db_session):
        """GET /billing/plans is accessible without auth."""
        _seed_all_plans(db_session)

        response = client.get("/api/v1/billing/plans")
        assert response.status_code == 200

    def test_plan_response_shape(self, client, db_session):
        """GET /billing/plans response includes all expected fields."""
        _seed_all_plans(db_session)

        response = client.get("/api/v1/billing/plans")
        plan = response.json()["plans"][1]  # Creator plan
        assert plan["name"] == "creator"
        assert plan["display_name"] == "Creator"
        assert plan["price_cents"] == 1900
        assert plan["videos_per_month"] == 30
        assert plan["channels_limit"] == 3
        assert plan["team_seats"] == 1
        assert plan["overage_cents"] == 75
        assert "features" in plan


class TestCreateCheckoutSession:
    @patch("saas.services.billing_service.stripe")
    def test_create_checkout_session(self, mock_stripe, client, db_session):
        """POST /billing/checkout with valid plan returns checkout URL."""
        _seed_all_plans(db_session)
        headers, user = _auth_headers(db_session)

        # Mock Stripe Customer.create and checkout.Session.create
        mock_stripe.Customer.create.return_value = MagicMock(id="cus_test123")
        mock_stripe.checkout.Session.create.return_value = MagicMock(
            url="https://checkout.stripe.com/c/pay/test123"
        )

        response = client.post(
            "/api/v1/billing/checkout",
            json={"plan": "pro"},
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "checkout_url" in data
        assert data["checkout_url"] == "https://checkout.stripe.com/c/pay/test123"

    def test_create_checkout_invalid_plan(self, client, db_session):
        """POST /billing/checkout with invalid plan returns 400."""
        headers, user = _auth_headers(db_session)

        response = client.post(
            "/api/v1/billing/checkout",
            json={"plan": "nonexistent"},
            headers=headers,
        )
        assert response.status_code == 400

    def test_create_checkout_unauthenticated(self, client, db_session):
        """POST /billing/checkout without auth returns 401."""
        response = client.post(
            "/api/v1/billing/checkout",
            json={"plan": "pro"},
        )
        assert response.status_code == 401


class TestStripeWebhook:
    def test_stripe_webhook_subscription_created(self, client, db_session):
        """POST /webhooks/stripe with subscription.created activates plan."""
        _seed_all_plans(db_session)
        headers, user = _auth_headers(db_session)

        pro_plan = db_session.query(Plan).filter(Plan.name == "pro").first()

        # Build a fake Stripe event payload
        import json
        import time

        event_payload = {
            "id": "evt_test123",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_test123",
                    "metadata": {
                        "user_id": str(user.id),
                        "plan": "pro",
                    },
                    "status": "active",
                    "current_period_start": int(time.time()),
                    "current_period_end": int(time.time()) + 30 * 86400,
                }
            },
        }
        raw_payload = json.dumps(event_payload)

        # Mock Stripe webhook signature verification
        with patch("saas.api.v1.webhooks.stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = event_payload

            response = client.post(
                "/api/v1/webhooks/stripe",
                content=raw_payload,
                headers={
                    "stripe-signature": "t=12345,v1=fakesig",
                    "content-type": "application/json",
                },
            )

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

        # Verify subscription was updated
        from saas.models.subscription import Subscription

        sub = (
            db_session.query(Subscription)
            .filter(Subscription.user_id == user.id)
            .first()
        )
        assert sub is not None
        assert sub.plan_id == pro_plan.id
        assert sub.stripe_subscription_id == "sub_test123"
        assert sub.status == "active"

    def test_stripe_webhook_missing_signature(self, client, db_session):
        """POST /webhooks/stripe without signature header returns 400."""
        response = client.post(
            "/api/v1/webhooks/stripe",
            content="{}",
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 400

    def test_stripe_webhook_subscription_deleted(self, client, db_session):
        """POST /webhooks/stripe with subscription.deleted downgrades to free."""
        _seed_all_plans(db_session)
        headers, user = _auth_headers(db_session)

        # First, set user to pro plan
        from saas.models.subscription import Subscription

        sub = db_session.query(Subscription).filter(Subscription.user_id == user.id).first()
        pro_plan = db_session.query(Plan).filter(Plan.name == "pro").first()
        sub.plan_id = pro_plan.id
        sub.stripe_subscription_id = "sub_to_delete"
        db_session.commit()

        import json

        event_payload = {
            "id": "evt_del_test",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_to_delete",
                    "metadata": {"user_id": str(user.id)},
                }
            },
        }

        with patch("saas.api.v1.webhooks.stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = event_payload

            response = client.post(
                "/api/v1/webhooks/stripe",
                content=json.dumps(event_payload),
                headers={
                    "stripe-signature": "t=12345,v1=fakesig",
                    "content-type": "application/json",
                },
            )

        assert response.status_code == 200

        db_session.refresh(sub)
        free_plan = db_session.query(Plan).filter(Plan.name == "free").first()
        assert sub.plan_id == free_plan.id
        assert sub.status == "canceled"
        assert sub.stripe_subscription_id is None

    def test_stripe_webhook_payment_failed(self, client, db_session):
        """POST /webhooks/stripe with invoice.payment_failed sets past_due."""
        _seed_all_plans(db_session)
        headers, user = _auth_headers(db_session)

        # Set stripe_customer_id on user
        user.stripe_customer_id = "cus_test_pf"
        db_session.commit()

        import json

        event_payload = {
            "id": "evt_pf_test",
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "customer": "cus_test_pf",
                }
            },
        }

        with patch("saas.api.v1.webhooks.stripe.Webhook.construct_event") as mock_construct:
            mock_construct.return_value = event_payload

            response = client.post(
                "/api/v1/webhooks/stripe",
                content=json.dumps(event_payload),
                headers={
                    "stripe-signature": "t=12345,v1=fakesig",
                    "content-type": "application/json",
                },
            )

        assert response.status_code == 200

        from saas.models.subscription import Subscription

        sub = db_session.query(Subscription).filter(Subscription.user_id == user.id).first()
        assert sub.status == "past_due"
