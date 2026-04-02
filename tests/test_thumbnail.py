"""Tests for pipeline/thumbnail.py — text wrapping, title overlay, thumbnail generation."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from pipeline.thumbnail import (
    _wrap_text,
    _overlay_title,
    generate_thumbnail,
    THUMB_WIDTH,
    THUMB_HEIGHT,
)


def _make_draw():
    """Create a real PIL ImageDraw context for _wrap_text tests."""
    img = Image.new("RGB", (400, 400))
    return ImageDraw.Draw(img)


def _default_font():
    return ImageFont.load_default()


def _make_test_png(path: Path, size=(1280, 720), color=(80, 80, 80)):
    """Helper: create a real PNG at the given path."""
    img = Image.new("RGB", size, color)
    img.save(path)


class TestWrapText:
    def test_single_line(self):
        draw = _make_draw()
        font = _default_font()
        lines = _wrap_text(draw, "Hi", font, max_width=200)
        assert lines == ["Hi"]

    def test_multiple_lines(self):
        draw = _make_draw()
        font = _default_font()
        long_text = "This is a fairly long sentence that should wrap across multiple lines"
        lines = _wrap_text(draw, long_text, font, max_width=100)
        assert len(lines) > 1
        # All words should be present across the lines
        rejoined = " ".join(lines)
        assert rejoined == long_text

    def test_empty_string(self):
        draw = _make_draw()
        font = _default_font()
        lines = _wrap_text(draw, "", font, max_width=200)
        assert lines == []

    def test_single_long_word(self):
        draw = _make_draw()
        font = _default_font()
        # A single word that is wider than max_width still gets placed on a line
        word = "Supercalifragilisticexpialidocious"
        lines = _wrap_text(draw, word, font, max_width=50)
        assert len(lines) == 1
        assert lines[0] == word


class TestOverlayTitle:
    def test_creates_output(self, tmp_path):
        input_path = tmp_path / "raw.png"
        output_path = tmp_path / "final.png"
        _make_test_png(input_path, size=(800, 600))

        _overlay_title(input_path, "Test Title", output_path)

        assert output_path.exists()
        img = Image.open(output_path)
        assert img.size == (THUMB_WIDTH, THUMB_HEIGHT)


class TestGenerateThumbnail:
    def test_calls_gemini_and_overlay(self, tmp_path, mocker):
        mocker.patch("pipeline.thumbnail.get_gemini_key", return_value="test-key")

        def fake_generate(prompt, output_path, api_key):
            _make_test_png(output_path, size=(1280, 720))

        mocker.patch(
            "pipeline.thumbnail._generate_thumb_image",
            side_effect=fake_generate,
        )

        draft = {
            "job_id": "test123",
            "thumbnail_prompt": "A dramatic Bitcoin scene",
            "youtube_title": "Bitcoin Hits New High",
        }

        result = generate_thumbnail(draft, tmp_path)

        assert result.exists()
        assert result.name == "thumb_test123.png"
        img = Image.open(result)
        assert img.size == (THUMB_WIDTH, THUMB_HEIGHT)
