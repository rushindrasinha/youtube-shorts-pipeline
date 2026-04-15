from __future__ import annotations
"""NewsAPI topic source — requires NEWSAPI_KEY env var or config.json.

Gracefully skipped if NEWSAPI_KEY is absent — no errors raised.
Sign up at https://newsapi.org to get a free API key.
"""

from ..api_client import get_client
from ..config import get_newsapi_key
from ..log import log
from .base import TopicCandidate, TopicSource

# Niche → NewsAPI query string mapping
_NICHE_QUERIES: dict[str, str] = {
    "gaming":  "gaming video games",
    "finance": "finance markets investing",
    "fitness": "fitness health workout",
    "tech":    "technology AI startups",
    "beauty":  "beauty skincare makeup",
    "food":    "food recipes cooking",
    "travel":  "travel destinations",
    "general": "trending",
}


class NewsAPISource(TopicSource):
    """Fetch top headlines from NewsAPI.org for a given niche or query."""

    name = "newsapi"

    def __init__(self, config: dict | None = None):
        config = config or {}
        self._api_key = get_newsapi_key()
        # Explicit query overrides niche-based lookup
        self._query = config.get("query", "")
        self._niche = config.get("niche", "general")

    @property
    def is_available(self) -> bool:
        """NewsAPI is only available when an API key is configured."""
        return bool(self._api_key)

    def fetch_topics(self, limit: int = 10) -> list[TopicCandidate]:
        """Fetch top headlines; returns empty list if unavailable."""
        if not self._api_key:
            return []

        query = self._query or _NICHE_QUERIES.get(self._niche, "trending")

        try:
            data = get_client().get_json(
                "https://newsapi.org/v2/top-headlines",
                params={
                    "q": query,
                    "language": "en",
                    "pageSize": min(limit, 20),  # NewsAPI max per request
                },
                # API key sent via header, not URL param, to avoid leaking in logs
                headers={
                    "User-Agent": "verticals/3.0",
                    "X-Api-Key": self._api_key,
                },
                timeout=10,
            )
            articles = data.get("articles", [])
        except Exception as e:
            log(f"NewsAPI fetch failed: {e}")
            return []

        candidates = []
        for i, article in enumerate(articles[:limit]):
            title = (article.get("title") or "").strip()
            if not title or title == "[Removed]":
                continue
            # Rank-based score: first result = 1.0, decays 0.05 per position
            score = max(0.3, 1.0 - i * 0.05)
            candidates.append(TopicCandidate(
                title=title,
                source="newsapi",
                trending_score=score,
                summary=(article.get("description") or "")[:200],
                url=article.get("url") or "",
            ))

        return candidates
