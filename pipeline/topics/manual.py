"""Manual topic source — --news passthrough."""

from .base import TopicCandidate, TopicSource


class ManualSource(TopicSource):
    """Wraps a manually provided --news topic as a TopicCandidate."""

    name = "manual"

    def __init__(self, config: dict = None):
        pass

    def fetch_topics(self, limit: int = 10) -> list[TopicCandidate]:
        return []  # Manual source doesn't discover — it's a passthrough

    @staticmethod
    def from_news(news: str) -> TopicCandidate:
        return TopicCandidate(
            title=news,
            source="manual",
            trending_score=1.0,
        )
