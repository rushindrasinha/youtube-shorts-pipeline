"""Tests for pipeline/research.py — keyword extraction + research."""

from pipeline.config import extract_keywords


class TestExtractKeywords:
    def test_basic(self):
        result = extract_keywords("India wins VCT Pacific 2026")
        words = result.split()
        assert len(words) <= 4
        # Stopwords removed
        assert "the" not in words

    def test_removes_stopwords(self):
        result = extract_keywords("The new update is available for all users")
        words = result.split()
        assert "the" not in words
        assert "is" not in words
        assert "for" not in words
        assert "new" not in words

    def test_removes_short_words(self):
        result = extract_keywords("An AI is on a new PC")
        words = result.split()
        for w in words:
            assert len(w) > 2

    def test_strips_punctuation(self):
        result = extract_keywords('Hello, "world!" says (test)')
        words = result.split()
        for w in words:
            assert "," not in w
            assert '"' not in w
            assert "!" not in w

    def test_max_four_words(self):
        result = extract_keywords("one two three four five six seven eight nine ten")
        words = result.split()
        assert len(words) <= 4

    def test_empty_input(self):
        result = extract_keywords("")
        assert result == ""

    def test_all_stopwords(self):
        result = extract_keywords("the and or but in on at")
        assert result == ""
