"""Tests for pipeline/broll.py — b-roll generation, fallback frames, Ken Burns animation."""

from pathlib import Path
from unittest.mock import call

from PIL import Image

from pipeline.broll import _fallback_frame, generate_broll, animate_frame
from pipeline.config import VIDEO_WIDTH, VIDEO_HEIGHT


def _make_test_image(path: Path, size=(512, 512), color=(100, 100, 100)):
    """Helper: create a real PNG at the given path."""
    img = Image.new("RGB", size, color)
    img.save(path)


class TestFallbackFrame:
    def test_creates_correct_size(self, tmp_path):
        path = _fallback_frame(0, tmp_path)
        img = Image.open(path)
        assert img.size == (VIDEO_WIDTH, VIDEO_HEIGHT)

    def test_cycles_colors(self, tmp_path):
        pixels = []
        for i in range(4):
            path = _fallback_frame(i, tmp_path)
            img = Image.open(path)
            pixels.append(img.getpixel((0, 0)))

        # Indices 0, 1, 2 should each have different colors
        assert pixels[0] != pixels[1]
        assert pixels[1] != pixels[2]
        assert pixels[0] != pixels[2]
        # Index 3 cycles back to index 0's color
        assert pixels[3] == pixels[0]


class TestGenerateBroll:
    def _mock_gemini_success(self, prompt, out_path, api_key):
        """Side effect: writes a real 512x512 PNG to out_path."""
        _make_test_image(out_path, size=(512, 512))

    def test_success(self, tmp_path, mocker):
        mocker.patch("pipeline.broll.get_gemini_key", return_value="test-key")
        mocker.patch(
            "pipeline.broll._generate_image_gemini",
            side_effect=self._mock_gemini_success,
        )

        prompts = ["prompt A", "prompt B", "prompt C"]
        frames = generate_broll(prompts, tmp_path)

        assert len(frames) == 3
        for f in frames:
            assert f.exists()
            img = Image.open(f)
            assert img.size == (VIDEO_WIDTH, VIDEO_HEIGHT)

    def test_partial_failure(self, tmp_path, mocker):
        mocker.patch("pipeline.broll.get_gemini_key", return_value="test-key")

        call_count = 0

        def gemini_fails_on_second(prompt, out_path, api_key):
            nonlocal call_count
            if call_count == 1:
                call_count += 1
                raise RuntimeError("Gemini failed")
            call_count += 1
            _make_test_image(out_path, size=(512, 512))

        mocker.patch(
            "pipeline.broll._generate_image_gemini",
            side_effect=gemini_fails_on_second,
        )

        frames = generate_broll(["a", "b", "c"], tmp_path)

        assert len(frames) == 3
        for f in frames:
            assert f.exists()
            img = Image.open(f)
            assert img.size == (VIDEO_WIDTH, VIDEO_HEIGHT)

    def test_all_fail(self, tmp_path, mocker):
        mocker.patch("pipeline.broll.get_gemini_key", return_value="test-key")
        mocker.patch(
            "pipeline.broll._generate_image_gemini",
            side_effect=RuntimeError("Gemini down"),
        )

        frames = generate_broll(["a", "b", "c"], tmp_path)

        assert len(frames) == 3
        for f in frames:
            assert f.exists()
            img = Image.open(f)
            assert img.size == (VIDEO_WIDTH, VIDEO_HEIGHT)

    def test_truncates_to_three(self, tmp_path, mocker):
        mocker.patch("pipeline.broll.get_gemini_key", return_value="test-key")
        mock_gen = mocker.patch(
            "pipeline.broll._generate_image_gemini",
            side_effect=self._mock_gemini_success,
        )

        frames = generate_broll(["a", "b", "c", "d", "e"], tmp_path)

        assert len(frames) == 3
        assert mock_gen.call_count == 3

    def test_empty_prompts(self, tmp_path, mocker):
        mocker.patch("pipeline.broll.get_gemini_key", return_value="test-key")

        frames = generate_broll([], tmp_path)

        assert frames == []


class TestResizeCrop:
    """Test the resize/crop logic inside generate_broll by feeding non-standard images."""

    def _mock_gemini_with_size(self, size):
        def side_effect(prompt, out_path, api_key):
            _make_test_image(out_path, size=size)
        return side_effect

    def test_landscape_input(self, tmp_path, mocker):
        mocker.patch("pipeline.broll.get_gemini_key", return_value="test-key")
        mocker.patch(
            "pipeline.broll._generate_image_gemini",
            side_effect=self._mock_gemini_with_size((1920, 1080)),
        )

        frames = generate_broll(["landscape test"], tmp_path)

        assert len(frames) == 1
        img = Image.open(frames[0])
        assert img.size == (VIDEO_WIDTH, VIDEO_HEIGHT)

    def test_square_input(self, tmp_path, mocker):
        mocker.patch("pipeline.broll.get_gemini_key", return_value="test-key")
        mocker.patch(
            "pipeline.broll._generate_image_gemini",
            side_effect=self._mock_gemini_with_size((1000, 1000)),
        )

        frames = generate_broll(["square test"], tmp_path)

        assert len(frames) == 1
        img = Image.open(frames[0])
        assert img.size == (VIDEO_WIDTH, VIDEO_HEIGHT)


class TestAnimateFrame:
    def test_zoom_in_command(self, tmp_path, mocker):
        mock_run = mocker.patch("pipeline.broll.run_cmd")
        img_path = tmp_path / "frame.png"
        out_path = tmp_path / "animated.mp4"
        _make_test_image(img_path)

        animate_frame(img_path, out_path, duration=3.0, effect="zoom_in")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        vf_arg = cmd[cmd.index("-vf") + 1]
        # Zoom in: z starts at 1.0 and increases by 0.12 over frames
        assert "1.0+0.12*on/" in vf_arg
        assert "zoompan" in vf_arg

    def test_zoom_out_command(self, tmp_path, mocker):
        mock_run = mocker.patch("pipeline.broll.run_cmd")
        img_path = tmp_path / "frame.png"
        out_path = tmp_path / "animated.mp4"
        _make_test_image(img_path)

        animate_frame(img_path, out_path, duration=3.0, effect="zoom_out")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        vf_arg = cmd[cmd.index("-vf") + 1]
        # Zoom out: z starts at 1.12 and decreases by 0.12 over frames
        assert "1.12-0.12*on/" in vf_arg
        assert "zoompan" in vf_arg
