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


class TestRegister:
    """POST /api/v1/auth/register"""

    def test_register_creates_user(self, client):
        """Register a new user, verify 201 and cookies are set."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "display_name": "New User",
            },
        )
        assert response.status_code == 201
        data = response.json()

        # Verify response body
        assert "user" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["display_name"] == "New User"
        assert data["user"]["role"] == "user"
        assert "access_token" in data
        assert data["expires_in"] == 900

        # Verify httpOnly cookies are set
        cookies = response.cookies
        assert "access_token" in cookies

    def test_register_duplicate_email(self, client, db_session):
        """Registering with an existing email returns 409."""
        _create_test_user(db_session, email="dupe@example.com")

        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "dupe@example.com",
                "password": "anotherpassword123",
                "display_name": "Duplicate",
            },
        )
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"].lower()

    def test_register_short_password(self, client):
        """Password shorter than 8 chars is rejected with 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "short@example.com",
                "password": "short",
                "display_name": "Short Password",
            },
        )
        assert response.status_code == 422

    def test_register_invalid_email(self, client):
        """Invalid email format is rejected with 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "securepassword123",
            },
        )
        assert response.status_code == 422

    def test_register_creates_free_subscription(self, client):
        """Newly registered user gets a free plan subscription."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "freeplan@example.com",
                "password": "securepassword123",
                "display_name": "Free Plan User",
            },
        )
        assert response.status_code == 201
        data = response.json()
        sub = data["user"].get("subscription")
        assert sub is not None
        assert sub["plan"] == "free"
        assert sub["status"] == "active"


class TestLogin:
    """POST /api/v1/auth/login"""

    def test_login_success(self, client, db_session):
        """Login with valid credentials returns 200 and sets cookies."""
        _create_test_user(db_session, email="login@example.com", password="correctpassword")

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "login@example.com",
                "password": "correctpassword",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["expires_in"] == 900

        # Verify cookies
        cookies = response.cookies
        assert "access_token" in cookies

    def test_login_wrong_password(self, client, db_session):
        """Login with wrong password returns 401."""
        _create_test_user(db_session, email="wrongpw@example.com", password="correctpassword")

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "wrongpw@example.com",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client):
        """Login with unknown email returns 401."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nobody@example.com",
                "password": "anypassword",
            },
        )
        assert response.status_code == 401


class TestGetMe:
    """GET /api/v1/users/me"""

    def test_get_me_authenticated(self, client, db_session):
        """GET /users/me with valid JWT returns user data."""
        _create_test_user(db_session, email="me@example.com", password="testpassword123")

        # Login to get cookies
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "me@example.com", "password": "testpassword123"},
        )
        assert login_resp.status_code == 200
        access_token = login_resp.json()["access_token"]

        # Use Bearer header to get user profile
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "me@example.com"
        assert data["display_name"] == "Test User"
        assert data["role"] == "user"
        assert data["default_lang"] == "en"
        assert data["caption_style"] == "yellow_highlight"
        assert data["music_genre"] == "auto"

    def test_get_me_unauthenticated(self, client):
        """GET /users/me without token returns 401."""
        response = client.get("/api/v1/users/me")
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client):
        """GET /users/me with invalid token returns 401."""
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401


class TestUpdateMe:
    """PATCH /api/v1/users/me"""

    def test_update_me(self, client, db_session):
        """PATCH /users/me updates allowed fields."""
        _create_test_user(db_session, email="update@example.com", password="testpassword123")

        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "update@example.com", "password": "testpassword123"},
        )
        access_token = login_resp.json()["access_token"]

        response = client.patch(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "display_name": "Updated Name",
                "default_lang": "hi",
                "caption_style": "news_style",
                "music_genre": "upbeat",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Updated Name"
        assert data["default_lang"] == "hi"
        assert data["caption_style"] == "news_style"
        assert data["music_genre"] == "upbeat"


class TestRefresh:
    """POST /api/v1/auth/refresh"""

    def test_refresh_without_token(self, client):
        """POST /auth/refresh without cookie returns 401."""
        response = client.post("/api/v1/auth/refresh")
        assert response.status_code == 401

    def test_refresh_with_valid_token(self, client, db_session):
        """POST /auth/refresh with valid refresh token rotates tokens."""
        _create_test_user(db_session, email="refresh@example.com", password="testpassword123")

        # Login to get tokens
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": "refresh@example.com", "password": "testpassword123"},
        )
        assert login_resp.status_code == 200

        # Extract refresh_token from Set-Cookie headers
        # The TestClient stores cookies, but refresh_token has path restriction.
        # We need to get it from the raw response and set it manually.
        from saas.services.auth_service import create_refresh_token
        from saas.models.user import User

        user = db_session.query(User).filter(User.email == "refresh@example.com").first()
        refresh_tok = create_refresh_token(user)

        response = client.post(
            "/api/v1/auth/refresh",
            cookies={"refresh_token": refresh_tok},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["expires_in"] == 900


class TestLogout:
    """POST /api/v1/auth/logout"""

    def test_logout(self, client):
        """POST /auth/logout clears cookies and returns ok."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestHealth:
    """GET /api/v1/health"""

    def test_health(self, client):
        """GET /health returns ok."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
