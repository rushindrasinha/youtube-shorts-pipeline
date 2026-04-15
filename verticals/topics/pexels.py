"""Pexels-driven story discovery: photos inspire scripts."""

import os

import requests

from ..llm import call_llm
from ..log import log
from .base import TopicSource, TopicCandidate


class PexelsSource(TopicSource):
    """Discover stories by pulling trending Pexels photos and generating scripts around them."""

    name = "pexels"

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.niche = self.config.get("niche", "general")
        self.api_key = os.environ.get("PEXELS_API_KEY", "")
        self.enabled = self.config.get("enabled", bool(self.api_key))

    @property
    def is_available(self) -> bool:
        """Check if Pexels API key is configured."""
        return self.enabled and bool(self.api_key)

    def fetch_topics(self, limit: int = 3) -> list[TopicCandidate]:
        """Fetch trending Pexels photos, generate scripts, return as TopicCandidates."""
        if not self.is_available:
            return []

        try:
            stories = discover_stories_from_pexels(self.niche, limit)
            candidates = []

            for story in stories:
                candidate = TopicCandidate(
                    title=story["topic"],
                    source="pexels",
                    trending_score=0.75,  # Pexels stories are inherently curated (trending photos)
                    summary=story["hook"],
                    url=story["photo_url"],
                    metadata={
                        "script": story["script"],
                        "hook": story["hook"],
                        "photo_id": story["photo_id"],
                        "visual_desc": story["visual_desc"],
                    },
                )
                candidates.append(candidate)

            return candidates

        except Exception as e:
            log(f"Pexels fetch failed: {e}")
            return []


def extract_visual_keywords(photo: dict) -> str:
    """Extract keywords from Pexels photo metadata."""
    alt = photo.get("alt", "")
    photographer = photo.get("photographer", "")

    # Use photographer name as style hint if available
    keywords = []
    if alt:
        keywords.append(alt)
    if photographer:
        keywords.append(f"style: {photographer}")

    return " | ".join(keywords) if keywords else "Generic scene"


def discover_stories_from_pexels(niche: str, limit: int = 3) -> list[dict]:
    """Pull trending Pexels photos, extract visual themes, generate scripts around them.

    Args:
        niche: Story niche (reddit_stories, tech, ai, agentic_workflows)
        limit: Number of photos to process

    Returns:
        List of {photo_url, visual_desc, script, topic, hook}
    """
    api_key = os.environ.get("PEXELS_API_KEY", "")
    if not api_key:
        log("⚠️  PEXELS_API_KEY not set — skipping Pexels discovery")
        return []

    # Niche-specific search queries
    niche_queries = {
        "reddit_stories": "dramatic moment confrontation phone shock",
        "tech": "computer code laptop developer typing workspace",
        "ai": "artificial intelligence neural network robot machine learning",
        "agentic_workflows": "automation workflow process systems integration",
    }

    query = niche_queries.get(niche, "trending")

    try:
        # Pull curated/trending photos
        r = requests.get(
            "https://api.pexels.com/v1/search",
            params={
                "query": query,
                "per_page": limit,
                "orientation": "portrait",
                "size": "large",
            },
            headers={"Authorization": api_key},
            timeout=15,
        )

        if r.status_code != 200:
            log(f"Pexels API {r.status_code}: {r.text[:200]}")
            return []

        photos = r.json().get("photos", [])
        if not photos:
            log(f"No Pexels photos found for '{query}'")
            return []

        stories = []
        for i, photo in enumerate(photos[:limit]):
            visual_desc = extract_visual_keywords(photo)
            photo_url = photo["src"]["large"]
            photo_id = photo["id"]

            log(f"Generating script for Pexels photo {i+1}/{len(photos)}: {visual_desc[:50]}...")

            # Generate script matching the visual
            prompt = _build_niche_prompt(niche, visual_desc)

            try:
                response = call_llm(prompt, max_tokens=800)

                # Parse response (expect: hook\n\nscript\n\ntopic)
                lines = response.strip().split("\n\n")
                hook = lines[0] if len(lines) > 0 else "Unknown"
                script = lines[1] if len(lines) > 1 else response
                topic = lines[2] if len(lines) > 2 else visual_desc[:50]

                stories.append({
                    "photo_url": photo_url,
                    "photo_id": photo_id,
                    "visual_desc": visual_desc,
                    "hook": hook,
                    "script": script,
                    "topic": topic,
                    "niche": niche,
                    "source": "pexels",
                })

            except Exception as e:
                log(f"Script generation failed for photo {photo_id}: {e}")
                continue

        return stories

    except Exception as e:
        log(f"Pexels discovery failed: {e}")
        return []


def _build_niche_prompt(niche: str, visual_desc: str) -> str:
    """Build niche-specific prompt for script generation."""

    base = f"""You are a viral YouTube Shorts writer. A stock photo shows: {visual_desc}

Generate a compelling short-form video script that matches this visual.
Format your response as:
HOOK: [One shocking sentence that makes people stop scrolling]

SCRIPT: [90-120 word narrative that matches the visual mood]

TOPIC: [One-line title/summary]"""

    niche_additions = {
        "reddit_stories": """
The script should tell a real Reddit story angle that matches the visual emotion:
- Focus on human conflict, surprise, or betrayal
- Make it relatable but shocking
- Include a plot twist or unexpected outcome
""",
        "tech": """
The script should be about technology, software, or tech culture:
- Could be a debugging war story, code review horror, or tech startup moment
- Should appeal to developers/engineers
- Make a technical insight relatable and funny
""",
        "ai": """
The script should explore AI, machine learning, or the future of AI:
- Could be about AI replacing jobs, AI going wrong, or AI breakthroughs
- Balance skepticism with wonder
- Make AI implications personal and concrete
""",
        "agentic_workflows": """
The script should showcase automation, AI agents, or workflow systems:
- Focus on how automation saves/changes human work
- Real use case or scenario
- Show the before (manual chaos) and after (automated bliss)
""",
    }

    addition = niche_additions.get(niche, "")
    return base + addition
