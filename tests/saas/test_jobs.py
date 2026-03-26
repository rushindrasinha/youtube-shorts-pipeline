"""Tests for Jobs API endpoints."""

import sys
import os

import pytest

# Ensure the conftest path setup runs
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "api"))

from tests.saas.conftest import create_test_user


def _auth_headers(db_session, user=None):
    """Create auth headers with a valid JWT for the given user."""
    from saas.services.auth_service import create_access_token

    if user is None:
        user = create_test_user(db_session)
    token = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}, user


class TestCreateJob:
    def test_create_job(self, client, db_session):
        """POST /jobs with valid topic returns 202."""
        headers, user = _auth_headers(db_session)
        response = client.post(
            "/api/v1/jobs",
            json={"topic": "SpaceX successfully lands Starship"},
            headers=headers,
        )
        assert response.status_code == 202
        data = response.json()
        assert data["topic"] == "SpaceX successfully lands Starship"
        assert data["status"] == "queued"
        assert data["progress_pct"] == 0
        assert "id" in data

    def test_create_job_validation_empty_topic(self, client, db_session):
        """POST /jobs with empty topic returns 422."""
        headers, user = _auth_headers(db_session)
        response = client.post(
            "/api/v1/jobs",
            json={"topic": ""},
            headers=headers,
        )
        assert response.status_code == 422

    def test_create_job_validation_short_topic(self, client, db_session):
        """POST /jobs with topic too short returns 422."""
        headers, user = _auth_headers(db_session)
        response = client.post(
            "/api/v1/jobs",
            json={"topic": "ab"},
            headers=headers,
        )
        assert response.status_code == 422

    def test_create_job_invalid_language(self, client, db_session):
        """POST /jobs with invalid language returns 422."""
        headers, user = _auth_headers(db_session)
        response = client.post(
            "/api/v1/jobs",
            json={"topic": "A valid topic here", "language": "fr"},
            headers=headers,
        )
        assert response.status_code == 422

    def test_create_job_invalid_privacy(self, client, db_session):
        """POST /jobs with invalid upload_privacy returns 422."""
        headers, user = _auth_headers(db_session)
        response = client.post(
            "/api/v1/jobs",
            json={"topic": "A valid topic here", "upload_privacy": "invalid"},
            headers=headers,
        )
        assert response.status_code == 422

    def test_create_job_with_all_fields(self, client, db_session):
        """POST /jobs with all optional fields."""
        headers, user = _auth_headers(db_session)
        response = client.post(
            "/api/v1/jobs",
            json={
                "topic": "SpaceX successfully lands Starship",
                "context": "Tech news channel",
                "language": "hi",
                "voice_id": "test-voice-id",
                "caption_style": "news_style",
                "music_genre": "upbeat",
                "auto_upload": False,
                "upload_privacy": "unlisted",
            },
            headers=headers,
        )
        assert response.status_code == 202
        data = response.json()
        assert data["topic"] == "SpaceX successfully lands Starship"

    def test_create_job_unauthenticated(self, client):
        """POST /jobs without auth returns 401."""
        response = client.post(
            "/api/v1/jobs",
            json={"topic": "SpaceX successfully lands Starship"},
        )
        assert response.status_code == 401


class TestListJobs:
    def test_list_jobs_empty(self, client, db_session):
        """GET /jobs returns empty list for new user."""
        headers, user = _auth_headers(db_session)
        response = client.get("/api/v1/jobs", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["has_more"] is False
        assert data["next_cursor"] is None

    def test_list_jobs_returns_created(self, client, db_session):
        """GET /jobs returns jobs after creation."""
        headers, user = _auth_headers(db_session)

        # Create a job
        client.post(
            "/api/v1/jobs",
            json={"topic": "Test topic for listing"},
            headers=headers,
        )

        response = client.get("/api/v1/jobs", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["topic"] == "Test topic for listing"

    def test_list_jobs_filter_by_status(self, client, db_session):
        """GET /jobs?status=queued filters correctly."""
        headers, user = _auth_headers(db_session)

        client.post(
            "/api/v1/jobs",
            json={"topic": "Job one"},
            headers=headers,
        )

        response = client.get("/api/v1/jobs?status=queued", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1

        response = client.get("/api/v1/jobs?status=completed", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 0

    def test_list_jobs_pagination(self, client, db_session):
        """GET /jobs with limit returns paginated results."""
        headers, user = _auth_headers(db_session)

        # Create 3 jobs
        for i in range(3):
            client.post(
                "/api/v1/jobs",
                json={"topic": f"Topic number {i}"},
                headers=headers,
            )

        # Get first page with limit=2
        response = client.get("/api/v1/jobs?limit=2", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["has_more"] is True
        assert data["next_cursor"] is not None

        # Get second page using cursor
        cursor = data["next_cursor"]
        response = client.get(f"/api/v1/jobs?limit=2&cursor={cursor}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["has_more"] is False


class TestGetJobDetail:
    def test_get_job_detail(self, client, db_session):
        """GET /jobs/{id} returns job with stages."""
        headers, user = _auth_headers(db_session)

        # Create a job
        create_resp = client.post(
            "/api/v1/jobs",
            json={"topic": "Detail test topic"},
            headers=headers,
        )
        job_id = create_resp.json()["id"]

        response = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id
        assert data["topic"] == "Detail test topic"
        assert len(data["stages"]) == 8  # All pipeline stages
        assert data["draft_data"] is None  # Not included by default

    def test_get_job_detail_with_draft_data(self, client, db_session):
        """GET /jobs/{id}?include=draft_data includes draft."""
        headers, user = _auth_headers(db_session)

        create_resp = client.post(
            "/api/v1/jobs",
            json={"topic": "Draft data test"},
            headers=headers,
        )
        job_id = create_resp.json()["id"]

        response = client.get(
            f"/api/v1/jobs/{job_id}?include=draft_data", headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        # draft_data is included (empty dict for new job)
        assert "draft_data" in data

    def test_get_job_not_found(self, client, db_session):
        """GET /jobs/{id} with non-existent ID returns 404."""
        headers, user = _auth_headers(db_session)
        response = client.get(
            "/api/v1/jobs/00000000-0000-0000-0000-000000000000",
            headers=headers,
        )
        assert response.status_code == 404

    def test_get_job_other_user(self, client, db_session):
        """GET /jobs/{id} for another user's job returns 404."""
        headers1, user1 = _auth_headers(db_session, email="user1@example.com")
        headers2, user2 = _auth_headers(db_session, email="user2@example.com")

        # User 1 creates a job
        create_resp = client.post(
            "/api/v1/jobs",
            json={"topic": "User 1 job"},
            headers=headers1,
        )
        job_id = create_resp.json()["id"]

        # User 2 tries to access it
        response = client.get(f"/api/v1/jobs/{job_id}", headers=headers2)
        assert response.status_code == 404


class TestCancelJob:
    def test_cancel_job(self, client, db_session):
        """DELETE /jobs/{id} sets status to canceled."""
        headers, user = _auth_headers(db_session)

        create_resp = client.post(
            "/api/v1/jobs",
            json={"topic": "Cancel test topic"},
            headers=headers,
        )
        job_id = create_resp.json()["id"]

        response = client.delete(f"/api/v1/jobs/{job_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "canceled"

        # Verify persisted
        detail_resp = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert detail_resp.json()["status"] == "canceled"

    def test_cancel_job_not_found(self, client, db_session):
        """DELETE /jobs/{id} with non-existent ID returns 404."""
        headers, user = _auth_headers(db_session)
        response = client.delete(
            "/api/v1/jobs/00000000-0000-0000-0000-000000000000",
            headers=headers,
        )
        assert response.status_code == 404


class TestRetryJob:
    def test_retry_failed_job(self, client, db_session):
        """POST /jobs/{id}/retry re-enqueues a failed job."""
        headers, user = _auth_headers(db_session)

        # Create and manually set to failed
        create_resp = client.post(
            "/api/v1/jobs",
            json={"topic": "Retry test topic"},
            headers=headers,
        )
        job_id = create_resp.json()["id"]

        # Manually set status to failed in DB
        from saas.models.job import Job

        job = db_session.query(Job).filter(Job.id == job_id).first()
        job.status = "failed"
        job.error_message = "Test failure"
        db_session.commit()

        response = client.post(f"/api/v1/jobs/{job_id}/retry", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"

    def test_retry_non_failed_job(self, client, db_session):
        """POST /jobs/{id}/retry on a queued job returns 409."""
        headers, user = _auth_headers(db_session)

        create_resp = client.post(
            "/api/v1/jobs",
            json={"topic": "Not failed topic"},
            headers=headers,
        )
        job_id = create_resp.json()["id"]

        response = client.post(f"/api/v1/jobs/{job_id}/retry", headers=headers)
        assert response.status_code == 409


class TestUsageLimits:
    def test_quota_exceeded(self, client, db_session):
        """POST /jobs returns 402 when quota is exceeded."""
        headers, user = _auth_headers(db_session)

        # Free plan allows 3 videos. Create 3 jobs.
        for i in range(3):
            resp = client.post(
                "/api/v1/jobs",
                json={"topic": f"Quota test topic {i}"},
                headers=headers,
            )
            assert resp.status_code == 202

        # 4th job should be rejected
        response = client.post(
            "/api/v1/jobs",
            json={"topic": "One too many"},
            headers=headers,
        )
        assert response.status_code == 402


def _auth_headers(db_session, email="test@example.com", user=None):
    """Create auth headers with a valid JWT for the given user."""
    from saas.services.auth_service import create_access_token

    if user is None:
        user = create_test_user(db_session, email=email)
    token = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}, user
