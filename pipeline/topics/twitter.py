"""Twitter/X topic source — optional, uses guest trends API."""

import requests

from .base import TopicCandidate, TopicSource


class TwitterSource(TopicSource):
    name = "twitter"

    def __init__(self, config: dict = None):
        config = config or {}
        self.enabled = config.get("enabled", False)

    @property
    def is_available(self) -> bool:
        return self.enabled

    def fetch_topics(self, limit: int = 10) -> list[TopicCandidate]:
        """Fetch trending topics from X/Twitter.

        Uses the public trends endpoint which doesn't require auth.
        Falls back gracefully if blocked.
        """
        try:
            # Twitter guest API for trends (may be rate-limited)
            url = "https://api.twitter.com/2/trends/by/woeid/1"
            headers = {"User-Agent": "yt-shorts-pipeline/2.0"}
            r = requests.get(url, headers=headers, timeout=10)

            if r.status_code != 200:
                return self._fallback_trends(limit)

            data = r.json()
            topics = []
            for trend in data.get("data", [])[:limit]:
                topics.append(TopicCandidate(
                    title=trend.get("trend_name", ""),
                    source="twitter",
                    trending_score=0.7,
                    metadata={"tweet_count": trend.get("tweet_count", 0)},
                ))
            return topics
        except Exception:
            return self._fallback_trends(limit)

    def _fallback_trends(self, limit: int) -> list[TopicCandidate]:
        """Fallback: return empty list if Twitter API is unavailable."""
        return []
