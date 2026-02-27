"""Shared test fixtures."""

import json
import pytest
from pathlib import Path


@pytest.fixture
def tmp_work_dir(tmp_path):
    """Create a temporary working directory."""
    work = tmp_path / "work"
    work.mkdir()
    return work


@pytest.fixture
def sample_draft():
    """A minimal draft dict for testing."""
    return {
        "job_id": "1234567890",
        "news": "Test news topic",
        "script": "This is a test script for a YouTube Short about testing.",
        "broll_prompts": ["Prompt 1", "Prompt 2", "Prompt 3"],
        "youtube_title": "Test Video Title",
        "youtube_description": "Test description",
        "youtube_tags": "test,video,short",
        "instagram_caption": "Test caption",
        "thumbnail_prompt": "A cinematic thumbnail",
        "research": "Some research data.",
    }


@pytest.fixture
def sample_words():
    """Sample Whisper word-level timestamps."""
    return [
        {"word": "This", "start": 0.0, "end": 0.3},
        {"word": "is", "start": 0.3, "end": 0.5},
        {"word": "a", "start": 0.5, "end": 0.6},
        {"word": "test", "start": 0.6, "end": 1.0},
        {"word": "of", "start": 1.2, "end": 1.4},
        {"word": "the", "start": 1.4, "end": 1.6},
        {"word": "caption", "start": 1.6, "end": 2.0},
        {"word": "system", "start": 2.0, "end": 2.5},
        {"word": "for", "start": 2.8, "end": 3.0},
        {"word": "YouTube", "start": 3.0, "end": 3.4},
        {"word": "Shorts", "start": 3.4, "end": 3.8},
        {"word": "pipeline", "start": 3.8, "end": 4.3},
    ]


@pytest.fixture
def sample_speech_regions():
    """Sample speech regions for ducking tests."""
    return [
        (0.0, 2.5),
        (2.8, 4.3),
    ]


@pytest.fixture
def draft_json_path(tmp_path, sample_draft):
    """Write sample draft to a temp file and return the path."""
    path = tmp_path / "test_draft.json"
    path.write_text(json.dumps(sample_draft, indent=2))
    return path
