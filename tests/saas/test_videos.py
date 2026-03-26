"""Tests for Videos API endpoints."""

import sys
import os
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "api"))

from saas.models.job import Job
from saas.models.video import Video
from tests.saas.conftest import create_test_user


def _auth_headers(db_session, email="videos-test@example.com", user=None):
    """Create auth headers with a valid JWT for the given user."""
    from saas.services.auth_service import create_access_token

    if user is None:
        user = create_test_user(db_session, email=email)
    token = create_access_token(user)
    return {"Authorization": f"Bearer {token}"}, user


def _create_test_video(db_session, user, title="Test Video"):
    """Create a job and video for testing."""
    job = Job(
        user_id=user.id,
        topic=f"Topic for {title}",
        status="completed",
        progress_pct=100,
    )
    db_session.add(job)
    db_session.flush()

    video = Video(
        job_id=job.id,
        user_id=user.id,
        title=title,
        video_url="https://media.shortfactory.io/test/final.mp4",
        video_s3_key=f"{user.id}/2026-03/{job.id}/final.mp4",
        thumbnail_url="https://media.shortfactory.io/test/thumb.jpg",
        thumbnail_s3_key=f"{user.id}/2026-03/{job.id}/thumb.jpg",
        duration_seconds=72.5,
        file_size_bytes=15728640,
        resolution="1080x1920",
        language="en",
    )
    db_session.add(video)
    db_session.commit()
    return video


class TestListVideos:
    def test_list_videos_empty(self, client, db_session):
        """GET /videos returns empty list for new user."""
        headers, user = _auth_headers(db_session)

        response = client.get("/api/v1/videos", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["has_more"] is False
        assert data["next_cursor"] is None

    def test_list_videos_returns_created(self, client, db_session):
        """GET /videos returns videos after creation."""
        headers, user = _auth_headers(db_session)
        _create_test_video(db_session, user, "My First Video")

        response = client.get("/api/v1/videos", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "My First Video"

    def test_list_videos_pagination(self, client, db_session):
        """GET /videos with limit returns paginated results."""
        headers, user = _auth_headers(db_session)

        for i in range(3):
            _create_test_video(db_session, user, f"Video {i}")

        # First page
        response = client.get("/api/v1/videos?limit=2", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["has_more"] is True
        assert data["next_cursor"] is not None

        # Second page
        cursor = data["next_cursor"]
        response = client.get(f"/api/v1/videos?limit=2&cursor={cursor}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["has_more"] is False

    def test_list_videos_unauthenticated(self, client):
        """GET /videos without auth returns 401."""
        response = client.get("/api/v1/videos")
        assert response.status_code == 401

    def test_list_videos_isolation(self, client, db_session):
        """GET /videos only returns the current user's videos."""
        headers1, user1 = _auth_headers(db_session, email="user1@vid.com")
        headers2, user2 = _auth_headers(db_session, email="user2@vid.com")

        _create_test_video(db_session, user1, "User 1 Video")
        _create_test_video(db_session, user2, "User 2 Video")

        response = client.get("/api/v1/videos", headers=headers1)
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "User 1 Video"


class TestGetVideo:
    def test_get_video_detail(self, client, db_session):
        """GET /videos/{id} returns full video details."""
        headers, user = _auth_headers(db_session)
        video = _create_test_video(db_session, user)

        response = client.get(f"/api/v1/videos/{video.id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(video.id)
        assert data["title"] == "Test Video"
        assert data["video_url"] is not None
        assert data["resolution"] == "1080x1920"

    def test_get_video_not_found(self, client, db_session):
        """GET /videos/{id} with non-existent ID returns 404."""
        headers, user = _auth_headers(db_session)

        response = client.get(
            "/api/v1/videos/00000000-0000-0000-0000-000000000000",
            headers=headers,
        )
        assert response.status_code == 404

    def test_get_video_other_user(self, client, db_session):
        """GET /videos/{id} for another user's video returns 404."""
        headers1, user1 = _auth_headers(db_session, email="owner@vid.com")
        headers2, user2 = _auth_headers(db_session, email="other@vid.com")

        video = _create_test_video(db_session, user1)

        response = client.get(f"/api/v1/videos/{video.id}", headers=headers2)
        assert response.status_code == 404


class TestDownloadVideo:
    @patch("saas.api.v1.videos.StorageService")
    def test_download_video(self, mock_storage_cls, client, db_session):
        """GET /videos/{id}/download returns presigned URL."""
        headers, user = _auth_headers(db_session)
        video = _create_test_video(db_session, user)

        mock_storage = MagicMock()
        mock_storage.get_presigned_url.return_value = (
            "https://s3.example.com/presigned/final.mp4?token=abc"
        )
        mock_storage_cls.return_value = mock_storage

        response = client.get(
            f"/api/v1/videos/{video.id}/download", headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "download_url" in data
        assert data["download_url"].startswith("https://")
        assert data["expires_in"] == 3600

        mock_storage.get_presigned_url.assert_called_once_with(
            video.video_s3_key, expires_in=3600
        )

    def test_download_video_not_found(self, client, db_session):
        """GET /videos/{id}/download for non-existent video returns 404."""
        headers, user = _auth_headers(db_session)

        response = client.get(
            "/api/v1/videos/00000000-0000-0000-0000-000000000000/download",
            headers=headers,
        )
        assert response.status_code == 404


class TestDeleteVideo:
    @patch("saas.api.v1.videos.StorageService")
    def test_delete_video(self, mock_storage_cls, client, db_session):
        """DELETE /videos/{id} removes video and S3 files."""
        headers, user = _auth_headers(db_session)
        video = _create_test_video(db_session, user)
        video_id = video.id

        mock_storage = MagicMock()
        mock_storage_cls.return_value = mock_storage

        response = client.delete(f"/api/v1/videos/{video_id}", headers=headers)
        assert response.status_code == 204

        # Verify deleted from DB
        remaining = db_session.query(Video).filter(Video.id == video_id).first()
        assert remaining is None

        # Verify S3 delete was called
        assert mock_storage.delete_file.call_count >= 1

    def test_delete_video_not_found(self, client, db_session):
        """DELETE /videos/{id} for non-existent video returns 404."""
        headers, user = _auth_headers(db_session)

        response = client.delete(
            "/api/v1/videos/00000000-0000-0000-0000-000000000000",
            headers=headers,
        )
        assert response.status_code == 404
