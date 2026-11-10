"""Tests for verticals/broll.py — Pollinations image generation."""

import io
from unittest.mock import patch

import pytest
from PIL import Image

from verticals.broll import (
    _generate_image_pollinations,
    generate_broll,
)
from verticals.config import VIDEO_WIDTH, VIDEO_HEIGHT


def _png_bytes(width=100, height=200, color=(200, 30, 30)):
    """A small valid PNG as bytes, for mocking Pollinations responses."""
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


class _FakeResponse:
    def __init__(self, status_code=200, content=b"", content_type="image/png"):
        self.status_code = status_code
        self.content = content
        self.headers = {"Content-Type": content_type}
        self.text = content.decode("utf-8", "replace")[:200]


class TestGenerateImagePollinations:
    @patch("verticals.broll.time.sleep")
    @patch("verticals.broll.requests.get")
    def test_gets_pollinations_and_writes_bytes(self, mock_get, mock_sleep, tmp_path):
        mock_get.return_value = _FakeResponse(content=_png_bytes())
        out = tmp_path / "frame.png"
        _generate_image_pollinations("a red sunset over mountains", out)
        assert out.read_bytes() == _png_bytes()
        url = mock_get.call_args.args[0]
        assert url.startswith("https://image.pollinations.ai/prompt/")
        assert "a%20red%20sunset%20over%20mountains" in url
        assert "width=1080&height=1920&nologo=true" in url
        mock_sleep.assert_called_once_with(16)

    @patch("verticals.retry.time.sleep")
    @patch("verticals.broll.requests.get")
    def test_non_200_raises(self, mock_get, mock_sleep, tmp_path):
        mock_get.return_value = _FakeResponse(
            status_code=429, content=b"rate limited", content_type="text/plain"
        )
        with pytest.raises(RuntimeError, match="Pollinations API 429"):
            _generate_image_pollinations("test", tmp_path / "frame.png")

    @patch("verticals.retry.time.sleep")
    @patch("verticals.broll.requests.get")
    def test_non_image_content_raises(self, mock_get, mock_sleep, tmp_path):
        mock_get.return_value = _FakeResponse(
            content=b"<html>not an image</html>", content_type="text/html"
        )
        with pytest.raises(RuntimeError, match="non-image content"):
            _generate_image_pollinations("test", tmp_path / "frame.png")


class TestGenerateBroll:
    @patch("verticals.broll.time.sleep")
    @patch("verticals.broll.requests.get")
    def test_generates_frames_without_any_api_key(
        self, mock_get, mock_sleep, tmp_work_dir
    ):
        # No GEMINI_API_KEY (or any key) is involved: Pollinations is keyless.
        mock_get.return_value = _FakeResponse(content=_png_bytes())
        with patch.dict("os.environ", {}, clear=False):
            frames = generate_broll(["p1", "p2", "p3"], tmp_work_dir)
        assert len(frames) == 3
        for frame in frames:
            assert frame.exists()
            img = Image.open(frame)
            assert img.size == (VIDEO_WIDTH, VIDEO_HEIGHT)

    @patch("verticals.broll._generate_image_pollinations")
    def test_failed_frame_falls_back(self, mock_gen, tmp_work_dir):
        mock_gen.side_effect = RuntimeError("Pollinations API 500")
        frames = generate_broll(["p1"], tmp_work_dir)
        assert len(frames) == 1
        assert frames[0].exists()
        assert Image.open(frames[0]).size == (VIDEO_WIDTH, VIDEO_HEIGHT)
