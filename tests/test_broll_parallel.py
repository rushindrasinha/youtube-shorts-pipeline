"""Tests for parallel b-roll generation in pipeline.broll."""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

from pipeline.broll import generate_broll


def test_broll_generates_3_frames_concurrently():
    """Verify generate_broll uses ThreadPoolExecutor for concurrent generation."""
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        prompts = ["prompt A", "prompt B", "prompt C"]

        # Track that ThreadPoolExecutor is used
        original_executor = ThreadPoolExecutor
        executor_used = []

        class TrackingExecutor(original_executor):
            def __init__(self, *args, **kwargs):
                executor_used.append(kwargs.get("max_workers", None))
                super().__init__(*args, **kwargs)

        with patch("pipeline.broll.ThreadPoolExecutor", TrackingExecutor), \
             patch("pipeline.broll._generate_image_gemini") as mock_gemini, \
             patch("pipeline.broll.get_gemini_key", return_value="fake-key"):

            # Make _generate_image_gemini write a valid image file
            def fake_generate(prompt, out_path, api_key):
                from PIL import Image
                img = Image.new("RGB", (1080, 1920), (100, 100, 100))
                img.save(out_path)

            mock_gemini.side_effect = fake_generate

            frames = generate_broll(prompts, out_dir)

        # ThreadPoolExecutor was used with max_workers=3
        assert len(executor_used) == 1
        assert executor_used[0] == 3

        # All 3 frames were generated
        assert len(frames) == 3
        assert all(f is not None for f in frames)
        assert all(f.exists() for f in frames)

        # Gemini was called 3 times (once per frame)
        assert mock_gemini.call_count == 3


def test_broll_uses_config_api_key():
    """When config is provided, use config.gemini_api_key instead of global."""
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        prompts = ["prompt A", "prompt B", "prompt C"]

        mock_config = MagicMock()
        mock_config.gemini_api_key = "injected-key"

        with patch("pipeline.broll._generate_image_gemini") as mock_gemini:
            def fake_generate(prompt, out_path, api_key):
                from PIL import Image
                img = Image.new("RGB", (1080, 1920), (50, 50, 50))
                img.save(out_path)

            mock_gemini.side_effect = fake_generate

            frames = generate_broll(prompts, out_dir, config=mock_config)

        # Verify the injected key was used in all calls
        for call in mock_gemini.call_args_list:
            assert call[0][2] == "injected-key"


def test_broll_fallback_on_failure():
    """If Gemini fails, fallback frames are generated."""
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp)
        prompts = ["fail1", "fail2", "fail3"]

        with patch("pipeline.broll._generate_image_gemini", side_effect=RuntimeError("API error")), \
             patch("pipeline.broll.get_gemini_key", return_value="fake-key"):

            frames = generate_broll(prompts, out_dir)

        # All 3 fallback frames should exist
        assert len(frames) == 3
        assert all(f.exists() for f in frames)
