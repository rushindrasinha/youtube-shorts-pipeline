"""Google Trends topic source via pytrends."""

from .base import TopicCandidate, TopicSource


class GoogleTrendsSource(TopicSource):
    name = "google_trends"

    def __init__(self, config: dict = None):
        config = config or {}
        self.geo = config.get("geo", "IN")

    @property
    def is_available(self) -> bool:
        try:
            from pytrends.request import TrendReq  # noqa: F401
            return True
        except ImportError:
            return False

    def fetch_topics(self, limit: int = 10) -> list[TopicCandidate]:
        from pytrends.request import TrendReq

        pytrends = TrendReq(hl="en-US", tz=330)  # IST offset
        trending = pytrends.trending_searches(pn=self._geo_to_pn())

        topics = []
        for i, row in trending.head(limit).iterrows():
            title = str(row[0])
            # Score decreases with rank
            score = max(0.1, 1.0 - (i * 0.05))
            topics.append(TopicCandidate(
                title=title,
                source="google_trends",
                trending_score=score,
            ))

        return topics

    def _geo_to_pn(self) -> str:
        """Convert geo code to pytrends pn parameter."""
        geo_map = {
            "IN": "india",
            "US": "united_states",
            "GB": "united_kingdom",
            "AU": "australia",
        }
        return geo_map.get(self.geo, "india")
