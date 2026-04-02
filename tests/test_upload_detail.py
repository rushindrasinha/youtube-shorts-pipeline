"""Tests for pipeline/upload.py — tag filtering, title truncation, OAuth, upload chain."""

from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

import pytest


# upload_to_youtube is wrapped with @with_retry(max_retries=2, base_delay=5.0).
# Patch time.sleep globally for all tests in this module so retries do not
# introduce 15+ seconds of real waiting.
pytestmark = pytest.mark.usefixtures("_patch_sleep")


@pytest.fixture(autouse=True)
def _patch_sleep():
    with patch("time.sleep"):
        yield


class TestOAuth:
    """Test credential refresh logic in upload_to_youtube."""

    @patch("pipeline.upload.write_secret_file")
    @patch("pipeline.upload.get_youtube_token_path")
    @patch("google.oauth2.credentials.Credentials")
    def test_expired_token_without_refresh_raises(
        self, MockCredentials, mock_token_path, mock_write_secret
    ):
        mock_token_path.return_value = Path("/fake/token.json")

        mock_creds = MagicMock()
        mock_creds.expired = True
        mock_creds.refresh_token = None
        MockCredentials.from_authorized_user_file.return_value = mock_creds

        from pipeline.upload import upload_to_youtube

        with pytest.raises(RuntimeError, match="expired and has no refresh token"):
            upload_to_youtube(
                video_path=Path("/fake/video.mp4"),
                draft={"news": "test", "youtube_tags": ""},
            )

    @patch("googleapiclient.http.MediaFileUpload")
    @patch("googleapiclient.discovery.build")
    @patch("pipeline.upload.write_secret_file")
    @patch("pipeline.upload.get_youtube_token_path")
    @patch("google.oauth2.credentials.Credentials")
    @patch("google.auth.transport.requests.Request")
    def test_expired_token_with_refresh_calls_refresh(
        self,
        MockRequest,
        MockCredentials,
        mock_token_path,
        mock_write_secret,
        mock_build,
        mock_media_upload,
    ):
        mock_token_path.return_value = Path("/fake/token.json")

        mock_creds = MagicMock()
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_tok"
        mock_creds.to_json.return_value = '{"token": "refreshed"}'
        MockCredentials.from_authorized_user_file.return_value = mock_creds

        # Wire up the YouTube API mock chain so upload completes
        mock_youtube = MagicMock()
        mock_build.return_value = mock_youtube
        mock_insert_req = MagicMock()
        mock_insert_req.next_chunk.return_value = (None, {"id": "abc123"})
        mock_youtube.videos.return_value.insert.return_value = mock_insert_req

        from pipeline.upload import upload_to_youtube

        upload_to_youtube(
            video_path=Path("/fake/video.mp4"),
            draft={"news": "test", "youtube_tags": ""},
        )

        mock_creds.refresh.assert_called_once()
        mock_write_secret.assert_called_once_with(
            Path("/fake/token.json"), '{"token": "refreshed"}'
        )


class TestUploadReturnsUrl:
    """Test that a successful upload returns the expected youtu.be URL."""

    @patch("googleapiclient.http.MediaFileUpload")
    @patch("googleapiclient.discovery.build")
    @patch("pipeline.upload.write_secret_file")
    @patch("pipeline.upload.get_youtube_token_path")
    @patch("google.oauth2.credentials.Credentials")
    def test_upload_returns_youtube_url(
        self,
        MockCredentials,
        mock_token_path,
        mock_write_secret,
        mock_build,
        mock_media_upload,
    ):
        mock_token_path.return_value = Path("/fake/token.json")

        mock_creds = MagicMock()
        mock_creds.expired = False
        MockCredentials.from_authorized_user_file.return_value = mock_creds

        mock_youtube = MagicMock()
        mock_build.return_value = mock_youtube

        mock_insert_req = MagicMock()
        mock_insert_req.next_chunk.return_value = (None, {"id": "XYZZY42"})
        mock_youtube.videos.return_value.insert.return_value = mock_insert_req

        from pipeline.upload import upload_to_youtube

        url = upload_to_youtube(
            video_path=Path("/fake/video.mp4"),
            draft={"news": "test news", "youtube_tags": "a,b"},
        )

        assert url == "https://youtu.be/XYZZY42"

    @patch("googleapiclient.http.MediaFileUpload")
    @patch("googleapiclient.discovery.build")
    @patch("pipeline.upload.write_secret_file")
    @patch("pipeline.upload.get_youtube_token_path")
    @patch("google.oauth2.credentials.Credentials")
    def test_upload_body_structure(
        self,
        MockCredentials,
        mock_token_path,
        mock_write_secret,
        mock_build,
        mock_media_upload,
    ):
        """Verify the body dict passed to videos().insert() has correct structure."""
        mock_token_path.return_value = Path("/fake/token.json")

        mock_creds = MagicMock()
        mock_creds.expired = False
        MockCredentials.from_authorized_user_file.return_value = mock_creds

        mock_youtube = MagicMock()
        mock_build.return_value = mock_youtube

        mock_insert_req = MagicMock()
        mock_insert_req.next_chunk.return_value = (None, {"id": "VID1"})
        mock_youtube.videos.return_value.insert.return_value = mock_insert_req

        from pipeline.upload import upload_to_youtube

        upload_to_youtube(
            video_path=Path("/fake/video.mp4"),
            draft={
                "news": "fallback title",
                "youtube_title": "X" * 150,
                "youtube_description": "desc here",
                "youtube_tags": "tag1,,tag2, ,tag3",
            },
        )

        # Inspect the body kwarg passed to insert()
        call_kwargs = mock_youtube.videos.return_value.insert.call_args
        body = call_kwargs.kwargs.get("body") or call_kwargs[1].get("body")

        assert len(body["snippet"]["title"]) == 100
        assert body["snippet"]["description"] == "desc here"
        assert body["snippet"]["tags"] == ["tag1", "tag2", "tag3"]
        assert body["snippet"]["categoryId"] == "20"
        assert body["status"]["privacyStatus"] == "private"
        assert body["status"]["selfDeclaredMadeForKids"] is False
