"""Tests for pipeline/config.py — key resolution, utilities."""

import json
import os
from pathlib import Path
from unittest.mock import patch

from pipeline.config import _get_key, extract_keywords, load_config


class TestGetKey:
    def test_env_var_priority(self):
        with patch.dict(os.environ, {"TEST_API_KEY": "from_env"}):
            assert _get_key("TEST_API_KEY") == "from_env"

    def test_returns_empty_for_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            assert _get_key("NONEXISTENT_KEY_XYZ") == ""

    @patch("pipeline.config.CONFIG_FILE")
    def test_reads_from_config(self, mock_path):
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = json.dumps({"MY_KEY": "from_config"})

        with patch.dict(os.environ, {}, clear=True):
            result = _get_key("MY_KEY")
            assert result == "from_config"


class TestExtractKeywords:
    def test_basic_extraction(self):
        result = extract_keywords("The quick brown fox jumps over the lazy dog")
        words = result.split()
        assert "the" not in words
        assert "over" not in words
        assert len(words) <= 4

    def test_lowercase(self):
        result = extract_keywords("UPPER Case Words HERE")
        for w in result.split():
            assert w == w.lower()


class TestLoadConfig:
    @patch("pipeline.config.CONFIG_FILE")
    def test_loads_valid_json(self, mock_path):
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = json.dumps({"key": "value"})
        assert load_config() == {"key": "value"}

    @patch("pipeline.config.CONFIG_FILE")
    def test_returns_empty_for_missing(self, mock_path):
        mock_path.exists.return_value = False
        assert load_config() == {}

    @patch("pipeline.config.CONFIG_FILE")
    def test_returns_empty_for_invalid_json(self, mock_path):
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = "not json"
        assert load_config() == {}
