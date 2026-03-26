"""Tests for pipeline.adapter — PipelineJob and JobConfig."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from pipeline.config import JobConfig
from pipeline.adapter import PipelineJob


def test_job_config_defaults():
    """Verify JobConfig has sensible defaults for all fields."""
    config = JobConfig()
    assert config.job_id == ""
    assert config.work_dir is None
    assert config.topic == ""
    assert config.context == ""
    assert config.anthropic_api_key == ""
    assert config.gemini_api_key == ""
    assert config.elevenlabs_api_key == ""
    assert config.voice_id == "JBFqnCBsd6RMkjVDRZzb"
    assert config.language == "en"
    assert config.caption_style == "yellow_highlight"
    assert config.music_genre == "auto"
    assert config.video_width == 1080
    assert config.video_height == 1920
    assert config.youtube_access_token == ""
    assert config.youtube_refresh_token == ""
    assert config.on_progress is None
    assert config.on_log is None


def test_pipeline_job_construction():
    """Verify PipelineJob creates work_dir and sets up job_id."""
    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp) / "test_job"
        config = JobConfig(
            job_id="test-123",
            work_dir=work_dir,
            topic="Test topic",
        )
        job = PipelineJob(config)
        assert job.job_id == "test-123"
        assert job.work_dir == work_dir
        assert work_dir.exists()
        assert job.draft == {}
        assert job.state is None


def test_pipeline_job_construction_auto_id():
    """When job_id is empty, PipelineJob generates a UUID."""
    with tempfile.TemporaryDirectory() as tmp:
        config = JobConfig(work_dir=Path(tmp))
        job = PipelineJob(config)
        assert job.job_id != ""
        assert len(job.job_id) == 36  # UUID4 format


def test_pipeline_job_construction_auto_workdir():
    """When work_dir is None, PipelineJob creates a temp directory."""
    config = JobConfig(job_id="auto-dir-test")
    job = PipelineJob(config)
    assert job.work_dir.exists()
    assert "sf_auto-dir-test_" in str(job.work_dir)


def test_pipeline_job_emits_progress():
    """Verify on_progress is called during pipeline execution."""
    progress_calls = []

    def track_progress(stage, status, pct, artifacts):
        progress_calls.append((stage, status, pct))

    with tempfile.TemporaryDirectory() as tmp:
        config = JobConfig(
            job_id="progress-test",
            work_dir=Path(tmp),
            topic="Test topic",
            on_progress=track_progress,
        )
        job = PipelineJob(config)

        # Mock all pipeline stages
        mock_draft = {
            "script": "Test script",
            "broll_prompts": ["prompt1", "prompt2", "prompt3"],
            "youtube_title": "Test",
            "news": "Test topic",
        }

        with patch("pipeline.draft.generate_draft", return_value=mock_draft) as mock_gen, \
             patch("pipeline.broll.generate_broll", return_value=[Path(tmp) / "f.png"] * 3), \
             patch("pipeline.voiceover.generate_voiceover", return_value=Path(tmp) / "vo.mp3"), \
             patch("pipeline.captions.generate_captions", return_value={"srt_path": "", "ass_path": ""}), \
             patch("pipeline.music.select_and_prepare_music", return_value={}), \
             patch("pipeline.assemble.assemble_video", return_value=Path(tmp) / "video.mp4"), \
             patch("pipeline.thumbnail.generate_thumbnail", return_value=Path(tmp) / "thumb.png"):

            result = job.run()

        assert result["status"] == "completed"
        # Verify progress was emitted for key stages
        stages_reported = [call[0] for call in progress_calls]
        assert "research" in stages_reported
        assert "draft" in stages_reported
        assert "broll" in stages_reported
        assert "voiceover" in stages_reported
        assert "captions" in stages_reported
        assert "music" in stages_reported
        assert "assemble" in stages_reported
        assert "thumbnail" in stages_reported


def test_pipeline_job_handles_failure():
    """Simulate an exception during pipeline execution and verify error in result."""
    with tempfile.TemporaryDirectory() as tmp:
        config = JobConfig(
            job_id="fail-test",
            work_dir=Path(tmp),
            topic="Fail topic",
        )
        job = PipelineJob(config)

        with patch("pipeline.draft.generate_draft", side_effect=RuntimeError("API down")):
            result = job.run()

        assert result["status"] == "failed"
        assert result["job_id"] == "fail-test"
        assert "API down" in result["error"]
