"""Reddit .json API topic source (hot/trending)."""

import requests

from .base import TopicCandidate, TopicSource


class RedditSource(TopicSource):
    name = "reddit"

    def __init__(self, config: dict = None):
        config = config or {}
        self.subreddits = config.get("subreddits", ["technology", "worldnews"])

    def fetch_topics(self, limit: int = 10) -> list[TopicCandidate]:
        topics = []
        per_sub = max(1, limit // len(self.subreddits))

        for sub in self.subreddits:
            try:
                topics.extend(self._fetch_subreddit(sub, per_sub))
            except Exception:
                continue

        return topics[:limit]

    def _fetch_subreddit(self, subreddit: str, limit: int) -> list[TopicCandidate]:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json"
        headers = {"User-Agent": "yt-shorts-pipeline/2.0"}
        r = requests.get(url, headers=headers, params={"limit": limit + 2}, timeout=10)
        r.raise_for_status()
        data = r.json()

        topics = []
        for post in data.get("data", {}).get("children", []):
            d = post.get("data", {})
            if d.get("stickied"):
                continue

            score = d.get("score", 0)
            # Normalize score: 10K+ = 1.0, logarithmic scale
            import math
            normalized = min(1.0, math.log10(max(score, 1)) / 4)

            topics.append(TopicCandidate(
                title=d.get("title", ""),
                source=f"reddit/r/{subreddit}",
                trending_score=normalized,
                summary=d.get("selftext", "")[:200],
                url=f"https://reddit.com{d.get('permalink', '')}",
                metadata={"score": score, "num_comments": d.get("num_comments", 0)},
            ))

        return topics
