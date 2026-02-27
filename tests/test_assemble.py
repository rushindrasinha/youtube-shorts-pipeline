"""Tests for pipeline/assemble.py — audio duration parsing."""

from unittest.mock import patch, MagicMock
from pathlib import Path

from pipeline.assemble import get_audio_duration


class TestGetAudioDuration:
    @patch("pipeline.assemble.run_cmd")
    def test_parses_duration(self, mock_cmd):
        mock_result = MagicMock()
        mock_result.stdout = "65.432000\n"
        mock_cmd.return_value = mock_result

        duration = get_audio_duration(Path("/tmp/test.mp3"))
        assert abs(duration - 65.432) < 0.001

    @patch("pipeline.assemble.run_cmd")
    def test_parses_short_duration(self, mock_cmd):
        mock_result = MagicMock()
        mock_result.stdout = "3.5\n"
        mock_cmd.return_value = mock_result

        duration = get_audio_duration(Path("/tmp/test.mp3"))
        assert abs(duration - 3.5) < 0.001

    @patch("pipeline.assemble.run_cmd")
    def test_calls_ffprobe(self, mock_cmd):
        mock_result = MagicMock()
        mock_result.stdout = "10.0\n"
        mock_cmd.return_value = mock_result

        get_audio_duration(Path("/tmp/audio.mp3"))
        args = mock_cmd.call_args[0][0]
        assert "ffprobe" in args
        assert "/tmp/audio.mp3" in args
