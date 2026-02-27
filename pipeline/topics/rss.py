"""RSS/Atom feed topic source."""

from .base import TopicCandidate, TopicSource


class RSSSource(TopicSource):
    name = "rss"

    def __init__(self, config: dict = None):
        config = config or {}
        self.feeds = config.get("feeds", ["https://hnrss.org/frontpage"])

    @property
    def is_available(self) -> bool:
        try:
            import feedparser  # noqa: F401
            return True
        except ImportError:
            return False

    def fetch_topics(self, limit: int = 10) -> list[TopicCandidate]:
        import feedparser

        topics = []
        per_feed = max(1, limit // len(self.feeds))

        for feed_url in self.feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:per_feed]:
                    topics.append(TopicCandidate(
                        title=entry.get("title", ""),
                        source=f"rss/{feed.feed.get('title', feed_url)[:30]}",
                        trending_score=0.5,  # RSS doesn't have scores
                        summary=entry.get("summary", "")[:200],
                        url=entry.get("link", ""),
                    ))
            except Exception:
                continue

        return topics[:limit]
