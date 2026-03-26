"""Tests for channels API — list, connect, OAuth flow."""

import sys
import os

import pytest

# Add apps/api to path so saas package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "api"))


def _create_test_user(db_session, email="test@example.com", password="testpassword123"):
    """Helper to create a test user directly in the DB."""
    from saas.models.user import User
    from saas.models.subscription import Plan, Subscription
    from saas.services.auth_service import hash_password

    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name="Test User",
    )
    db_session.add(user)
    db_session.flush()

    free_plan = db_session.query(Plan).filter(Plan.name == "free").first()
    if free_plan:
        sub = Subscription(
            user_id=user.id,
            plan_id=free_plan.id,
            status="active",
        )
        db_session.add(sub)

    db_session.commit()
    db_session.refresh(user)
    return user


def _login(client, email, password="testpassword123"):
    """Login and return access token."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


class TestListChannels:
    """GET /api/v1/channels"""

    def test_list_channels_empty(self, client, db_session):
        """A new user has no connected channels."""
        _create_test_user(db_session, email="nochannels@example.com")
        token = _login(client, "nochannels@example.com")

        response = client.get(
            "/api/v1/channels",
            headers=_auth_headers(token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    def test_list_channels_unauthenticated(self, client):
        """Unauthenticated request returns 401."""
        response = client.get("/api/v1/channels")
        assert response.status_code == 401


class TestConnectChannel:
    """POST /api/v1/channels/connect"""

    def test_connect_returns_oauth_url(self, client, db_session):
        """POST /channels/connect returns an OAuth authorization URL."""
        _create_test_user(db_session, email="connect@example.com")
        token = _login(client, "connect@example.com")

        response = client.post(
            "/api/v1/channels/connect",
            headers=_auth_headers(token),
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert "auth_url" in data
        assert "accounts.google.com" in data["auth_url"]

    def test_connect_team_channel_requires_admin(self, client, db_session):
        """Connecting a channel with team_id requires admin role."""
        from saas.models.subscription import Plan
        from saas.models.team import Team, TeamMember
        import uuid

        user = _create_test_user(db_session, email="teamch@example.com")
        viewer = _create_test_user(db_session, email="viewer@example.com")

        # Create a team plan and team
        plan = Plan(
            name="agency",
            display_name="Agency",
            videos_per_month=500,
            channels_limit=-1,
            team_seats=10,
            price_cents=14900,
            overage_cents=40,
            features={},
        )
        db_session.add(plan)
        db_session.commit()

        from saas.services.team_service import TeamService
        from saas.models.subscription import Subscription

        # Upgrade user to agency plan
        sub = db_session.query(Subscription).filter(Subscription.user_id == user.id).first()
        sub.plan_id = plan.id
        db_session.commit()

        service = TeamService(db_session)
        team = service.create_team(owner=user, name="Channel Test Team")

        # Add viewer
        db_session.add(
            TeamMember(team_id=team.id, user_id=viewer.id, role="viewer")
        )
        db_session.commit()

        # Viewer tries to connect team channel — should fail
        viewer_token = _login(client, "viewer@example.com")
        response = client.post(
            "/api/v1/channels/connect",
            headers=_auth_headers(viewer_token),
            json={"team_id": str(team.id)},
        )
        assert response.status_code == 403
