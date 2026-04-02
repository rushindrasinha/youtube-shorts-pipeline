"""Tests for pipeline/topics/engine.py — TopicEngine discovery, dedup, ranking, auto_pick."""

from unittest.mock import patch, MagicMock

import pytest

from pipeline.topics.base import TopicCandidate
from pipeline.topics.engine import TopicEngine


def _make_candidate(title, source="test", score=0.5):
    """Helper to create a TopicCandidate with defaults."""
    return TopicCandidate(title=title, source=source, trending_score=score)


def _make_mock_source(name, topics, available=True):
    """Create a mock topic source with the given name, topics, and availability."""
    src = MagicMock()
    src.name = name
    src.is_available = available
    src.fetch_topics.return_value = topics
    return src


def _make_engine(sources):
    """Create a TopicEngine with _sources injected, bypassing __init__."""
    engine = TopicEngine.__new__(TopicEngine)
    engine._sources = sources
    return engine


class TestDedup:
    """Test deduplication by first 50 chars of lowered, stripped title."""

    def test_removes_duplicates_by_title_prefix(self):
        """Two candidates whose first 50 chars match should be deduped to one."""
        prefix = "A" * 50
        source = _make_mock_source("s1", [
            _make_candidate(prefix + " - extra suffix one", score=0.9),
            _make_candidate(prefix + " - extra suffix two", score=0.8),
        ])
        engine = _make_engine([source])
        results = engine.discover(limit=15)
        assert len(results) == 1

    def test_keeps_different_titles(self):
        """Candidates with different first-50-char prefixes should all be kept."""
        source = _make_mock_source("s1", [
            _make_candidate("Alpha topic about technology", score=0.9),
            _make_candidate("Beta topic about science", score=0.8),
            _make_candidate("Gamma topic about politics", score=0.7),
        ])
        engine = _make_engine([source])
        results = engine.discover(limit=15)
        assert len(results) == 3

    def test_dedup_is_case_insensitive(self):
        """Dedup key uses .lower(), so case should not matter."""
        source = _make_mock_source("s1", [
            _make_candidate("BREAKING NEWS: Major Event", score=0.9),
            _make_candidate("breaking news: major event", score=0.5),
        ])
        engine = _make_engine([source])
        results = engine.discover(limit=15)
        assert len(results) == 1

    def test_dedup_strips_title(self):
        """Dedup key uses .strip(), so leading/trailing whitespace is ignored."""
        source = _make_mock_source("s1", [
            _make_candidate("  Important Topic  ", score=0.9),
            _make_candidate("Important Topic", score=0.5),
        ])
        engine = _make_engine([source])
        results = engine.discover(limit=15)
        assert len(results) == 1

    def test_dedup_across_sources(self):
        """Duplicate titles from different sources should be deduped."""
        s1 = _make_mock_source("reddit", [
            _make_candidate("Same title here", source="reddit", score=0.9),
        ])
        s2 = _make_mock_source("rss", [
            _make_candidate("Same title here", source="rss", score=0.4),
        ])
        engine = _make_engine([s1, s2])
        results = engine.discover(limit=15)
        assert len(results) == 1


class TestSortByTrendingScore:
    """Test that results are sorted by trending_score descending."""

    def test_sort_by_trending_score(self):
        source = _make_mock_source("s1", [
            _make_candidate("Low", score=0.1),
            _make_candidate("High", score=0.9),
            _make_candidate("Mid", score=0.5),
        ])
        engine = _make_engine([source])
        results = engine.discover(limit=15)
        scores = [t.trending_score for t in results]
        assert scores == sorted(scores, reverse=True)
        assert results[0].title == "High"
        assert results[-1].title == "Low"


class TestDiscoverLimit:
    """Test that discover() respects the limit parameter."""

    def test_limits_results(self):
        topics = [_make_candidate(f"Topic {i}", score=float(i) / 10) for i in range(10)]
        source = _make_mock_source("s1", topics)
        engine = _make_engine([source])
        results = engine.discover(limit=3)
        assert len(results) == 3

    def test_returns_fewer_than_limit_when_not_enough(self):
        topics = [_make_candidate("Only one")]
        source = _make_mock_source("s1", topics)
        engine = _make_engine([source])
        results = engine.discover(limit=10)
        assert len(results) == 1


class TestDiscoverSourceFailure:
    """Test resilience when individual sources fail."""

    def test_handles_source_failure(self):
        """One source raising should not prevent results from other sources."""
        good_source = _make_mock_source("good", [
            _make_candidate("Good topic", score=0.8),
        ])
        bad_source = _make_mock_source("bad", [])
        bad_source.fetch_topics.side_effect = RuntimeError("Source down")

        engine = _make_engine([good_source, bad_source])
        results = engine.discover(limit=15)

        assert len(results) == 1
        assert results[0].title == "Good topic"

    def test_all_sources_fail_returns_empty(self):
        """If every source fails, discover() should return an empty list."""
        bad1 = _make_mock_source("bad1", [])
        bad1.fetch_topics.side_effect = RuntimeError("fail 1")
        bad2 = _make_mock_source("bad2", [])
        bad2.fetch_topics.side_effect = RuntimeError("fail 2")

        engine = _make_engine([bad1, bad2])
        results = engine.discover(limit=15)
        assert results == []


class TestDiscoverParallelFetch:
    """Test that discover fetches from all available sources."""

    def test_fetches_all_sources(self):
        s1 = _make_mock_source("reddit", [_make_candidate("From reddit", score=0.7)])
        s2 = _make_mock_source("rss", [_make_candidate("From rss", score=0.6)])
        s3 = _make_mock_source("trends", [_make_candidate("From trends", score=0.5)])

        engine = _make_engine([s1, s2, s3])
        results = engine.discover(limit=15)

        s1.fetch_topics.assert_called_once_with(15)
        s2.fetch_topics.assert_called_once_with(15)
        s3.fetch_topics.assert_called_once_with(15)
        assert len(results) == 3

    def test_skips_unavailable_sources(self):
        """Sources with is_available=False should not be fetched."""
        available = _make_mock_source("good", [_make_candidate("Available")])
        unavailable = _make_mock_source("bad", [_make_candidate("Unavailable")], available=False)

        engine = _make_engine([available, unavailable])
        results = engine.discover(limit=15)

        available.fetch_topics.assert_called_once()
        unavailable.fetch_topics.assert_not_called()
        assert len(results) == 1
        assert results[0].title == "Available"


class TestAutoPick:
    """Test auto_pick sends candidates to Claude and returns the response."""

    @patch("pipeline.topics.engine.get_anthropic_client")
    @patch("pipeline.topics.engine.get_claude_backend", return_value="api")
    def test_returns_claude_api_response(self, mock_backend, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text="  Best topic here  ")]
        mock_client.messages.create.return_value = mock_msg

        engine = _make_engine([])
        candidates = [
            _make_candidate("Topic A", score=0.9),
            _make_candidate("Topic B", score=0.7),
        ]

        result = engine.auto_pick(candidates)

        assert result == "Best topic here"
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-sonnet-4-6"
        assert call_kwargs["max_tokens"] == 200

    @patch("pipeline.topics.engine.call_claude_cli", return_value="CLI picked topic")
    @patch("pipeline.topics.engine.get_claude_backend", return_value="cli")
    def test_falls_back_to_cli(self, mock_backend, mock_cli):
        engine = _make_engine([])
        candidates = [_make_candidate("Topic X", score=0.8)]

        result = engine.auto_pick(candidates)

        assert result == "CLI picked topic"
        mock_cli.assert_called_once()
        prompt_arg = mock_cli.call_args[0][0]
        assert "Topic X" in prompt_arg

    @patch("pipeline.topics.engine.get_anthropic_client")
    @patch("pipeline.topics.engine.get_claude_backend", return_value="api")
    def test_prompt_includes_candidate_titles(self, mock_backend, mock_get_client):
        """The prompt sent to Claude should include all candidate titles."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text="Chosen")]
        mock_client.messages.create.return_value = mock_msg

        engine = _make_engine([])
        candidates = [
            _make_candidate("Alpha headline", score=0.9),
            _make_candidate("Beta headline", score=0.7),
            _make_candidate("Gamma headline", score=0.5),
        ]

        engine.auto_pick(candidates)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        prompt = call_kwargs["messages"][0]["content"]
        assert "Alpha headline" in prompt
        assert "Beta headline" in prompt
        assert "Gamma headline" in prompt

    @patch("pipeline.topics.engine.get_anthropic_client")
    @patch("pipeline.topics.engine.get_claude_backend", return_value="api")
    def test_limits_candidates_to_20(self, mock_backend, mock_get_client):
        """auto_pick should only include the first 20 candidates in the prompt."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text="Picked")]
        mock_client.messages.create.return_value = mock_msg

        engine = _make_engine([])
        candidates = [_make_candidate(f"Topic {i}", score=0.5) for i in range(30)]

        engine.auto_pick(candidates)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        prompt = call_kwargs["messages"][0]["content"]
        assert "Topic 19" in prompt
        assert "Topic 20" not in prompt
