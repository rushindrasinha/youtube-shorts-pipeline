"""Tests for pipeline/music.py — duck filter generation, speech region merging."""

from pipeline.music import build_duck_filter


class TestBuildDuckFilter:
    def test_empty_regions(self):
        result = build_duck_filter([])
        assert result == "volume=0.25"

    def test_single_region(self):
        result = build_duck_filter([(1.0, 3.0)])
        assert "volume=" in result
        assert "between(t," in result
        assert "0.12" in result
        assert "0.25" in result

    def test_multiple_regions(self, sample_speech_regions):
        result = build_duck_filter(sample_speech_regions)
        assert result.count("between(t,") == 2
        assert "0.12" in result
        assert "0.25" in result
        assert "eval=frame" in result

    def test_buffer_applied(self):
        result = build_duck_filter([(1.0, 2.0)], buffer=0.5)
        # Start should be max(0, 1.0-0.5) = 0.5
        # End should be 2.0+0.5 = 2.5
        assert "0.50" in result
        assert "2.50" in result

    def test_buffer_no_negative_start(self):
        result = build_duck_filter([(0.1, 1.0)], buffer=0.3)
        # Start should be max(0, 0.1-0.3) = 0.0
        assert "0.00" in result

    def test_returns_ffmpeg_filter_format(self, sample_speech_regions):
        result = build_duck_filter(sample_speech_regions)
        # Should be a valid ffmpeg volume filter
        assert result.startswith("volume=")
        assert ":eval=frame" in result

    def test_if_expression_structure(self):
        result = build_duck_filter([(5.0, 10.0)])
        assert "if(" in result
        assert ", 0.12, 0.25)" in result
