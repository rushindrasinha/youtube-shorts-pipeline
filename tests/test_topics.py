"""Tests for pipeline/topics/ — TopicCandidate, sources, engine."""

from unittest.mock import patch, MagicMock

from pipeline.topics.base import TopicCandidate, TopicSource
from pipeline.topics.manual import ManualSource
from pipeline.topics.reddit import RedditSource


class TestTopicCandidate:
    def test_creation(self):
        t = TopicCandidate(title="Test", source="manual")
        assert t.title == "Test"
        assert t.source == "manual"
        assert t.trending_score == 0.0

    def test_with_score(self):
        t = TopicCandidate(title="Hot Topic", source="reddit", trending_score=0.85)
        assert t.trending_score == 0.85

    def test_metadata(self):
        t = TopicCandidate(title="T", source="s", metadata={"score": 5000})
        assert t.metadata["score"] == 5000


class TestManualSource:
    def test_from_news(self):
        topic = ManualSource.from_news("Breaking news headline")
        assert topic.title == "Breaking news headline"
        assert topic.source == "manual"
        assert topic.trending_score == 1.0

    def test_fetch_returns_empty(self):
        src = ManualSource()
        assert src.fetch_topics() == []


class TestRedditSource:
    def test_init_defaults(self):
        src = RedditSource()
        assert src.subreddits == ["technology", "worldnews"]

    def test_init_custom_subs(self):
        src = RedditSource({"subreddits": ["gaming", "science"]})
        assert src.subreddits == ["gaming", "science"]

    @patch("pipeline.topics.reddit.requests.get")
    def test_fetch_parses_reddit_json(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "Test Post 1",
                            "score": 15000,
                            "selftext": "Body text",
                            "permalink": "/r/technology/comments/abc/test",
                            "num_comments": 500,
                            "stickied": False,
                        }
                    },
                    {
                        "data": {
                            "title": "Stickied Post",
                            "score": 100,
                            "selftext": "",
                            "permalink": "/r/technology/comments/def/sticky",
                            "num_comments": 10,
                            "stickied": True,
                        }
                    },
                    {
                        "data": {
                            "title": "Test Post 2",
                            "score": 500,
                            "selftext": "",
                            "permalink": "/r/technology/comments/ghi/test2",
                            "num_comments": 50,
                            "stickied": False,
                        }
                    },
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        src = RedditSource({"subreddits": ["technology"]})
        topics = src.fetch_topics(limit=10)

        assert len(topics) == 2  # stickied excluded
        assert topics[0].title == "Test Post 1"
        assert topics[0].trending_score > topics[1].trending_score
        assert topics[0].metadata["score"] == 15000

    @patch("pipeline.topics.reddit.requests.get")
    def test_fetch_handles_error(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        src = RedditSource({"subreddits": ["technology"]})
        topics = src.fetch_topics()
        assert topics == []


class TestTopicSourceABC:
    def test_cannot_instantiate_abc(self):
        """TopicSource is abstract and can't be instantiated directly."""
        import pytest
        with pytest.raises(TypeError):
            TopicSource()

    def test_concrete_class(self):
        class TestSource(TopicSource):
            name = "test"
            def fetch_topics(self, limit=10):
                return [TopicCandidate(title="T", source="test")]

        src = TestSource()
        assert src.is_available is True
        assert len(src.fetch_topics()) == 1
