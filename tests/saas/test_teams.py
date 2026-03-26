"""Tests for teams API — CRUD, invites, permissions, job visibility."""

import sys
import os
from uuid import UUID

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


def _create_team_plan(db_session):
    """Create an agency plan that supports teams."""
    from saas.models.subscription import Plan

    plan = db_session.query(Plan).filter(Plan.name == "agency").first()
    if plan:
        return plan

    plan = Plan(
        name="agency",
        display_name="Agency",
        videos_per_month=500,
        channels_limit=-1,
        team_seats=10,
        price_cents=14900,
        overage_cents=40,
        features={"teams": True},
    )
    db_session.add(plan)
    db_session.commit()
    return plan


def _upgrade_user_plan(db_session, user, plan_name="agency"):
    """Upgrade a user's subscription to the specified plan."""
    from saas.models.subscription import Plan, Subscription

    plan = db_session.query(Plan).filter(Plan.name == plan_name).first()
    if not plan:
        plan = _create_team_plan(db_session)

    sub = (
        db_session.query(Subscription)
        .filter(Subscription.user_id == user.id)
        .first()
    )
    if sub:
        sub.plan_id = plan.id
    else:
        sub = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            status="active",
        )
        db_session.add(sub)
    db_session.commit()


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


class TestCreateTeam:
    """POST /api/v1/teams"""

    def test_create_team(self, client, db_session):
        """Successfully create a team with an agency plan."""
        _create_team_plan(db_session)
        user = _create_test_user(db_session, email="teamowner@example.com")
        _upgrade_user_plan(db_session, user, "agency")
        token = _login(client, "teamowner@example.com")

        response = client.post(
            "/api/v1/teams",
            headers=_auth_headers(token),
            json={"name": "My Agency", "brand_color": "#FF5722"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "My Agency"
        assert data["slug"] == "my-agency"
        assert data["brand_color"] == "#FF5722"
        assert data["members_count"] == 1
        assert data["channels_count"] == 0

    def test_create_team_free_plan_rejected(self, client, db_session):
        """Free plan users cannot create teams."""
        user = _create_test_user(db_session, email="freeuser@example.com")
        token = _login(client, "freeuser@example.com")

        response = client.post(
            "/api/v1/teams",
            headers=_auth_headers(token),
            json={"name": "Should Fail"},
        )
        assert response.status_code == 403


class TestInviteMember:
    """POST /api/v1/teams/{id}/members/invite"""

    def test_invite_member(self, client, db_session):
        """Admin can invite a member to the team."""
        _create_team_plan(db_session)
        owner = _create_test_user(db_session, email="owner@example.com")
        _upgrade_user_plan(db_session, owner, "agency")
        token = _login(client, "owner@example.com")

        # Create team
        create_resp = client.post(
            "/api/v1/teams",
            headers=_auth_headers(token),
            json={"name": "Invite Test Team"},
        )
        assert create_resp.status_code == 201
        team_id = create_resp.json()["id"]

        # Invite a member
        invite_resp = client.post(
            f"/api/v1/teams/{team_id}/members/invite",
            headers=_auth_headers(token),
            json={"email": "newmember@example.com", "role": "member"},
        )
        assert invite_resp.status_code == 201
        data = invite_resp.json()
        assert data["email"] == "newmember@example.com"
        assert data["role"] == "member"
        assert "expires_at" in data

    def test_invite_by_viewer_rejected(self, client, db_session):
        """Viewers cannot invite members."""
        _create_team_plan(db_session)
        owner = _create_test_user(db_session, email="owner2@example.com")
        viewer = _create_test_user(db_session, email="viewer@example.com")
        _upgrade_user_plan(db_session, owner, "agency")

        owner_token = _login(client, "owner2@example.com")

        # Create team
        create_resp = client.post(
            "/api/v1/teams",
            headers=_auth_headers(owner_token),
            json={"name": "Viewer Test Team"},
        )
        team_id = create_resp.json()["id"]

        # Add viewer as a member manually
        from saas.models.team import TeamMember

        db_session.add(
            TeamMember(
                team_id=UUID(team_id),
                user_id=viewer.id,
                role="viewer",
            )
        )
        db_session.commit()

        # Viewer tries to invite — should fail
        viewer_token = _login(client, "viewer@example.com")
        invite_resp = client.post(
            f"/api/v1/teams/{team_id}/members/invite",
            headers=_auth_headers(viewer_token),
            json={"email": "someone@example.com", "role": "member"},
        )
        assert invite_resp.status_code == 403


class TestPermissionCheck:
    """Verify the role hierarchy works correctly."""

    def test_permission_hierarchy(self, db_session):
        """Role hierarchy: owner > admin > member > viewer."""
        from saas.services.team_service import TeamService, ROLE_HIERARCHY

        assert ROLE_HIERARCHY["owner"] > ROLE_HIERARCHY["admin"]
        assert ROLE_HIERARCHY["admin"] > ROLE_HIERARCHY["member"]
        assert ROLE_HIERARCHY["member"] > ROLE_HIERARCHY["viewer"]

    def test_check_permission_grants_higher_roles(self, db_session):
        """A user with admin role passes a 'member' permission check."""
        _create_team_plan(db_session)
        from saas.services.team_service import TeamService
        from saas.models.team import Team, TeamMember

        owner = _create_test_user(db_session, email="permowner@example.com")
        _upgrade_user_plan(db_session, owner, "agency")

        service = TeamService(db_session)
        team = service.create_team(owner=owner, name="Perm Test Team")

        admin_user = _create_test_user(db_session, email="permadmin@example.com")
        db_session.add(
            TeamMember(team_id=team.id, user_id=admin_user.id, role="admin")
        )
        db_session.commit()

        # Admin should pass member check
        assert service.check_permission(admin_user.id, team.id, "member") is True
        # Admin should pass viewer check
        assert service.check_permission(admin_user.id, team.id, "viewer") is True
        # Admin should pass admin check
        assert service.check_permission(admin_user.id, team.id, "admin") is True
        # Admin should NOT pass owner check
        assert service.check_permission(admin_user.id, team.id, "owner") is False

    def test_non_member_has_no_permission(self, db_session):
        """A non-member fails all permission checks."""
        _create_team_plan(db_session)
        from saas.services.team_service import TeamService

        owner = _create_test_user(db_session, email="permowner2@example.com")
        _upgrade_user_plan(db_session, owner, "agency")

        service = TeamService(db_session)
        team = service.create_team(owner=owner, name="Perm Test Team 2")

        outsider = _create_test_user(db_session, email="outsider@example.com")
        assert service.check_permission(outsider.id, team.id, "viewer") is False


class TestTeamJobsVisibility:
    """Team members can see team jobs."""

    def test_team_jobs_visible_to_members(self, client, db_session):
        """A team member can list the team's jobs."""
        _create_team_plan(db_session)
        owner = _create_test_user(db_session, email="jobowner@example.com")
        member = _create_test_user(db_session, email="jobmember@example.com")
        _upgrade_user_plan(db_session, owner, "agency")

        owner_token = _login(client, "jobowner@example.com")

        # Create team
        create_resp = client.post(
            "/api/v1/teams",
            headers=_auth_headers(owner_token),
            json={"name": "Jobs Team"},
        )
        team_id = create_resp.json()["id"]

        # Add member
        from saas.models.team import TeamMember

        db_session.add(
            TeamMember(team_id=UUID(team_id), user_id=member.id, role="member")
        )
        db_session.commit()

        # Create a job assigned to the team
        from saas.models.job import Job

        job = Job(
            user_id=owner.id,
            team_id=UUID(team_id),
            topic="Team Job Topic",
            status="completed",
            progress_pct=100,
        )
        db_session.add(job)
        db_session.commit()

        # Member can see team jobs
        member_token = _login(client, "jobmember@example.com")
        jobs_resp = client.get(
            f"/api/v1/teams/{team_id}/jobs",
            headers=_auth_headers(member_token),
        )
        assert jobs_resp.status_code == 200
        items = jobs_resp.json()["items"]
        assert len(items) == 1
        assert items[0]["topic"] == "Team Job Topic"

    def test_non_member_cannot_see_team_jobs(self, client, db_session):
        """A non-member gets 403 when trying to list team jobs."""
        _create_team_plan(db_session)
        owner = _create_test_user(db_session, email="jobowner2@example.com")
        outsider = _create_test_user(db_session, email="outsider2@example.com")
        _upgrade_user_plan(db_session, owner, "agency")

        owner_token = _login(client, "jobowner2@example.com")

        create_resp = client.post(
            "/api/v1/teams",
            headers=_auth_headers(owner_token),
            json={"name": "Private Jobs Team"},
        )
        team_id = create_resp.json()["id"]

        outsider_token = _login(client, "outsider2@example.com")
        jobs_resp = client.get(
            f"/api/v1/teams/{team_id}/jobs",
            headers=_auth_headers(outsider_token),
        )
        assert jobs_resp.status_code == 403
