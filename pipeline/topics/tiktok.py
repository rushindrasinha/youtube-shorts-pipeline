"""TikTok trending topics source — optional, uses Apify or scraping."""

from .base import TopicCandidate, TopicSource


class TikTokSource(TopicSource):
    name = "tiktok"

    def __init__(self, config: dict = None):
        config = config or {}
        self.enabled = config.get("enabled", False)

    @property
    def is_available(self) -> bool:
        return self.enabled

    def fetch_topics(self, limit: int = 10) -> list[TopicCandidate]:
        """Fetch trending topics from TikTok.

        Currently a stub — requires Apify actor or direct scraping setup.
        """
        return []
