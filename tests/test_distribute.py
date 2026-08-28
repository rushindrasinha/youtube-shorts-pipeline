"""Tests for verticals/distribute.py — multi-platform publishing via Upload-Post."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from verticals import distribute


@pytest.fixture
def video_file(tmp_path):
    path = tmp_path / "short.mp4"
    path.write_bytes(b"fake-mp4-bytes")
    return path


def fake_response(status_code=200, payload=None, text=""):
    class Response:
        def __init__(self):
            self.status_code = status_code
            self.text = text

        def json(self):
            if payload is None:
                raise ValueError("no json")
            return payload

    return Response()


class TestParsePlatforms:
    def test_parses_and_normalizes(self):
        assert distribute.parse_platforms(" TikTok , instagram ") == ["tiktok", "instagram"]

    def test_empty_string_gives_empty_list(self):
        assert distribute.parse_platforms("") == []

    def test_rejects_unknown_platform(self):
        with pytest.raises(ValueError, match="myspace"):
            distribute.parse_platforms("tiktok,myspace")


class TestBuildPayload:
    def test_uses_youtube_title_as_default(self, sample_draft):
        payload = distribute.build_payload(sample_draft, ["tiktok"], "my-profile")
        assert payload["user"] == "my-profile"
        assert payload["title"] == sample_draft["youtube_title"]
        assert payload["platform[]"] == ["tiktok"]

    def test_falls_back_to_news_without_title(self):
        payload = distribute.build_payload({"news": "Big headline"}, ["tiktok"], "p")
        assert payload["title"] == "Big headline"

    def test_reuses_instagram_caption_from_draft(self, sample_draft):
        payload = distribute.build_payload(sample_draft, ["instagram"], "p")
        assert payload["instagram_title"] == sample_draft["instagram_caption"]

    def test_includes_description(self, sample_draft):
        payload = distribute.build_payload(sample_draft, ["youtube"], "p")
        assert payload["description"] == sample_draft["youtube_description"]

    def test_title_is_truncated(self):
        payload = distribute.build_payload({"youtube_title": "x" * 3000}, ["tiktok"], "p")
        assert len(payload["title"]) == 2200


class TestIsConfigured:
    def test_false_without_keys(self):
        with patch.object(distribute, "get_uploadpost_key", return_value=""), \
             patch.object(distribute, "get_uploadpost_user", return_value=""):
            assert distribute.is_configured() is False

    def test_true_with_both(self):
        with patch.object(distribute, "get_uploadpost_key", return_value="k"), \
             patch.object(distribute, "get_uploadpost_user", return_value="u"):
            assert distribute.is_configured() is True


class TestPublish:
    def _configured(self):
        return (
            patch.object(distribute, "get_uploadpost_key", return_value="test-key"),
            patch.object(distribute, "get_uploadpost_user", return_value="my-profile"),
        )

    def test_sends_multipart_with_apikey_scheme(self, video_file, sample_draft):
        captured = {}

        def fake_post(url, headers=None, data=None, files=None, timeout=None):
            captured.update(url=url, headers=headers, data=data, files=files)
            return fake_response(payload={"success": True, "request_id": "req_1"})

        key_patch, user_patch = self._configured()
        with key_patch, user_patch, patch.object(distribute.requests, "post", side_effect=fake_post):
            result = distribute.publish_to_platforms(
                video_file, sample_draft, ["tiktok", "instagram"])

        assert result["request_id"] == "req_1"
        assert captured["url"] == "https://api.upload-post.com/api/upload"
        # Upload-Post API keys use the Apikey scheme; Bearer returns a misleading 401
        assert captured["headers"]["Authorization"] == "Apikey test-key"
        assert captured["data"]["platform[]"] == ["tiktok", "instagram"]
        assert "video" in captured["files"]

    def test_schedule_and_timezone_are_sent(self, video_file, sample_draft):
        captured = {}

        def fake_post(url, headers=None, data=None, files=None, timeout=None):
            captured.update(data=data)
            return fake_response(payload={"success": True, "request_id": "req_2"})

        key_patch, user_patch = self._configured()
        with key_patch, user_patch, patch.object(distribute.requests, "post", side_effect=fake_post):
            distribute.publish_to_platforms(
                video_file, sample_draft, ["tiktok"],
                scheduled_date="2026-12-31T18:00:00Z", timezone="Europe/Madrid")

        assert captured["data"]["scheduled_date"] == "2026-12-31T18:00:00Z"
        assert captured["data"]["timezone"] == "Europe/Madrid"

    def test_unconfigured_raises(self, video_file, sample_draft):
        with patch.object(distribute, "get_uploadpost_key", return_value=""), \
             patch.object(distribute, "get_uploadpost_user", return_value=""):
            with pytest.raises(RuntimeError, match="not configured"):
                distribute.publish_to_platforms(video_file, sample_draft, ["tiktok"])

    def test_missing_video_raises(self, sample_draft, tmp_path):
        key_patch, user_patch = self._configured()
        with key_patch, user_patch:
            with pytest.raises(FileNotFoundError):
                distribute.publish_to_platforms(tmp_path / "nope.mp4", sample_draft, ["tiktok"])

    def test_no_platforms_raises(self, video_file, sample_draft):
        key_patch, user_patch = self._configured()
        with key_patch, user_patch:
            with pytest.raises(ValueError, match="No target platforms"):
                distribute.publish_to_platforms(video_file, sample_draft, [])

    def test_title_required_for_youtube(self, video_file):
        key_patch, user_patch = self._configured()
        with key_patch, user_patch:
            with pytest.raises(ValueError, match="title is required"):
                distribute.publish_to_platforms(video_file, {}, ["youtube"])

    def test_api_error_raises_with_message(self, video_file, sample_draft):
        key_patch, user_patch = self._configured()
        with key_patch, user_patch, \
             patch.object(distribute.requests, "post",
                          return_value=fake_response(401, {"error": "Invalid API key"})), \
             patch("time.sleep"):
            with pytest.raises(RuntimeError, match="Invalid API key"):
                distribute.publish_to_platforms(video_file, sample_draft, ["tiktok"])

    def test_non_json_response_raises(self, video_file, sample_draft):
        key_patch, user_patch = self._configured()
        with key_patch, user_patch, \
             patch.object(distribute.requests, "post",
                          return_value=fake_response(502, None, "<html>Bad Gateway</html>")), \
             patch("time.sleep"):
            with pytest.raises(RuntimeError, match="Bad Gateway"):
                distribute.publish_to_platforms(video_file, sample_draft, ["tiktok"])


class TestCheckStatus:
    def test_passes_request_id(self):
        captured = {}

        def fake_get(url, headers=None, params=None, timeout=None):
            captured.update(url=url, params=params)
            return fake_response(payload={"success": True, "status": "completed"})

        with patch.object(distribute, "get_uploadpost_key", return_value="k"), \
             patch.object(distribute.requests, "get", side_effect=fake_get):
            result = distribute.check_status("req_1")

        assert result["status"] == "completed"
        assert captured["params"]["request_id"] == "req_1"


class TestCliWiring:
    def test_distribute_is_a_pipeline_stage(self):
        from verticals.state import STAGES
        assert "distribute" in STAGES

    def test_state_records_request_id(self, sample_draft, tmp_path):
        from verticals.state import PipelineState
        state = PipelineState(sample_draft)
        state.complete_stage("distribute", {"request_id": "req_9", "platforms": ["tiktok"]})
        path = tmp_path / "draft.json"
        state.save(path)
        reloaded = json.loads(path.read_text())
        assert reloaded["_pipeline_state"]["distribute"]["artifacts"]["request_id"] == "req_9"
