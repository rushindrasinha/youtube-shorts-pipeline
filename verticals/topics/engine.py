"""TopicEngine — orchestrates multi-source discovery + Claude auto-pick."""

import concurrent.futures

from ..config import load_config, get_anthropic_client, get_claude_backend, call_claude_cli, NICHE_TO_SUBREDDITS
from ..log import log
from .base import TopicCandidate


class TopicEngine:
    """Fetches from all enabled sources, deduplicates, ranks."""

    def __init__(self, niche: str = "general"):
        self._niche = niche or "general"
        self._sources = []
        self._load_sources()

    def _load_sources(self):
        """Load enabled topic sources from config.

        When a niche is set, subreddit and NewsAPI query defaults are overridden
        with niche-appropriate values (user config.json can still override).
        """
        config = load_config()
        source_config = config.get("topic_sources", {})

        # Always register these — they'll check their own enabled status
        from .reddit import RedditSource
        from .rss import RSSSource
        from .google_trends import GoogleTrendsSource
        from .pexels import PexelsSource

        source_map = {
            "reddit": RedditSource,
            "rss": RSSSource,
            "google_trends": GoogleTrendsSource,
            "pexels": PexelsSource,
        }

        # Optional sources
        try:
            from .newsapi import NewsAPISource
            source_map["newsapi"] = NewsAPISource
        except ImportError:
            pass

        try:
            from .twitter import TwitterSource
            source_map["twitter"] = TwitterSource
        except ImportError:
            pass

        try:
            from .tiktok import TikTokSource
            source_map["tiktok"] = TikTokSource
        except ImportError:
            pass

        for name, cls in source_map.items():
            src_cfg = dict(source_config.get(name, {}))  # shallow copy so we can mutate

            # Apply niche defaults when no explicit config is set by user
            if self._niche != "general":
                if name == "reddit" and "subreddits" not in src_cfg:
                    niche_subs = NICHE_TO_SUBREDDITS.get(self._niche, [])
                    if niche_subs:
                        src_cfg["subreddits"] = niche_subs
                if name == "newsapi":
                    src_cfg.setdefault("niche", self._niche)

            # NewsAPI enabled if key is present (checked by is_available); others default on/off
            default_enabled = name in ("reddit", "rss", "google_trends", "newsapi", "pexels")
            if src_cfg.get("enabled", default_enabled):
                try:
                    self._sources.append(cls(src_cfg))
                except Exception as e:
                    log(f"Failed to init source {name}: {e}")

    def discover(self, limit: int = 15) -> list[TopicCandidate]:
        """Fetch from all sources in parallel, deduplicate, rank."""
        all_topics = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            futures = {
                pool.submit(src.fetch_topics, limit): src
                for src in self._sources if src.is_available
            }
            for future in concurrent.futures.as_completed(futures):
                src = futures[future]
                try:
                    topics = future.result(timeout=15)
                    all_topics.extend(topics)
                    log(f"{src.name}: found {len(topics)} topics")
                except Exception as e:
                    log(f"{src.name}: failed — {e}")

        # Deduplicate by fuzzy title matching
        seen = set()
        unique = []
        for t in all_topics:
            key = t.title.lower().strip()[:50]
            if key not in seen:
                seen.add(key)
                unique.append(t)

        # Sort by trending score (highest first)
        unique.sort(key=lambda t: t.trending_score, reverse=True)
        return unique[:limit]

    def auto_pick(self, candidates: list[TopicCandidate]) -> str:
        """Use Claude to pick the best topic for a YouTube Short."""
        topics_text = "\n".join(
            f"{i+1}. [{t.source}] {t.title} (score: {t.trending_score:.2f})"
            for i, t in enumerate(candidates[:20])
        )

        prompt = f"""Pick the single best topic from this list for a viral YouTube Short (60-90 sec).
Consider: visual potential, broad appeal, timeliness, controversy/surprise factor.

{topics_text}

Reply with ONLY the topic title text, nothing else."""

        backend = get_claude_backend()
        if backend == "api":
            client = get_anthropic_client()
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text.strip()
        else:
            return call_claude_cli(prompt, max_tokens=200)
