"""Tests for pipeline/captions.py — word grouping, ASS generation, SRT formatting."""

from pathlib import Path

from pipeline.captions import (
    _group_words,
    _format_ass_time,
    _generate_ass,
    _generate_srt,
    _srt_time,
)


class TestWordGrouping:
    def test_group_words_default_size(self, sample_words):
        groups = _group_words(sample_words)
        assert len(groups) == 3  # 12 words / 4 = 3 groups
        assert len(groups[0]) == 4
        assert len(groups[1]) == 4
        assert len(groups[2]) == 4

    def test_group_words_custom_size(self, sample_words):
        groups = _group_words(sample_words, group_size=3)
        assert len(groups) == 4  # 12 / 3 = 4
        assert len(groups[0]) == 3

    def test_group_words_single_word(self):
        words = [{"word": "Hello", "start": 0.0, "end": 0.5}]
        groups = _group_words(words)
        assert len(groups) == 1
        assert len(groups[0]) == 1

    def test_group_words_empty(self):
        groups = _group_words([])
        assert groups == []

    def test_group_words_uneven(self):
        words = [
            {"word": "one", "start": 0.0, "end": 0.3},
            {"word": "two", "start": 0.3, "end": 0.6},
            {"word": "three", "start": 0.6, "end": 0.9},
            {"word": "four", "start": 0.9, "end": 1.2},
            {"word": "five", "start": 1.2, "end": 1.5},
        ]
        groups = _group_words(words, group_size=4)
        assert len(groups) == 2
        assert len(groups[0]) == 4
        assert len(groups[1]) == 1


class TestASSTimeFormat:
    def test_zero(self):
        assert _format_ass_time(0.0) == "0:00:00.00"

    def test_seconds(self):
        assert _format_ass_time(5.5) == "0:00:05.50"

    def test_minutes(self):
        assert _format_ass_time(65.25) == "0:01:05.25"

    def test_hours(self):
        assert _format_ass_time(3661.75) == "1:01:01.75"

    def test_small_centiseconds(self):
        assert _format_ass_time(0.05) == "0:00:00.05"


class TestSRTTimeFormat:
    def test_zero(self):
        assert _srt_time(0.0) == "00:00:00,000"

    def test_seconds(self):
        assert _srt_time(5.5) == "00:00:05,500"

    def test_minutes(self):
        assert _srt_time(125.123) == "00:02:05,123"


class TestASSGeneration:
    def test_generates_file(self, sample_words, tmp_work_dir):
        output = tmp_work_dir / "test.ass"
        _generate_ass(sample_words, output)
        assert output.exists()
        content = output.read_text()
        assert "[Script Info]" in content
        assert "[V4+ Styles]" in content
        assert "[Events]" in content

    def test_contains_dialogue_lines(self, sample_words, tmp_work_dir):
        output = tmp_work_dir / "test.ass"
        _generate_ass(sample_words, output)
        content = output.read_text()
        assert "Dialogue:" in content

    def test_highlight_color_in_events(self, sample_words, tmp_work_dir):
        output = tmp_work_dir / "test.ass"
        _generate_ass(sample_words, output)
        content = output.read_text()
        # Yellow highlight color code
        assert "\\c&H00FFFF&" in content

    def test_word_count_events(self, sample_words, tmp_work_dir):
        """Each word in each group gets one dialogue line as active."""
        output = tmp_work_dir / "test.ass"
        _generate_ass(sample_words, output)
        content = output.read_text()
        dialogue_count = content.count("Dialogue:")
        # 3 groups * 4 words each = 12 dialogue lines
        assert dialogue_count == 12


class TestSRTGeneration:
    def test_generates_file(self, sample_words, tmp_work_dir):
        output = tmp_work_dir / "test.srt"
        _generate_srt(sample_words, output)
        assert output.exists()

    def test_srt_format(self, sample_words, tmp_work_dir):
        output = tmp_work_dir / "test.srt"
        _generate_srt(sample_words, output)
        content = output.read_text()
        assert "-->" in content
        assert "This is a test" in content

    def test_srt_group_count(self, sample_words, tmp_work_dir):
        output = tmp_work_dir / "test.srt"
        _generate_srt(sample_words, output)
        content = output.read_text()
        # 3 groups = 3 subtitle entries
        assert "1\n" in content
        assert "2\n" in content
        assert "3\n" in content
