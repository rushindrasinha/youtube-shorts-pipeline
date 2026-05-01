"""Hook intelligence layer — reverse-engineer successful hooks from YouTube channels."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import get_youtube_api_key
from .llm import call_llm
from .log import log
from .niche import load_niche, NICHES_DIR
import yaml


def fetch_channel_videos(
    channel_url: str,
    max_videos: int = 20,
) -> list[dict]:
    """
    Fetch top videos from a YouTube channel using the YouTube Data API.

    Args:
        channel_url: YouTube channel URL or @handle (e.g., "https://youtube.com/@mkbhd" or "@mkbhd")
        max_videos: Maximum number of videos to fetch

    Returns:
        List of dicts with: title, view_count, publish_date, video_id
    """
    api_key = get_youtube_api_key()
    if not api_key:
        raise ValueError(
            "YOUTUBE_API_KEY not found. Set via environment or ~/.verticals/config.json"
        )

    try:
        import google.auth.transport.requests
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError(
            "google-auth and google-api-python-client required. "
            "pip install google-auth google-api-python-client"
        )

    youtube = build("youtube", "v3", developerKey=api_key)

    # Extract channel handle from URL
    if "youtube.com/@" in channel_url:
        handle = channel_url.split("@")[-1].rstrip("/")
    elif channel_url.startswith("@"):
        handle = channel_url.lstrip("@")
    else:
        raise ValueError(
            f"Invalid channel URL. Use 'https://youtube.com/@HANDLE' or '@HANDLE'"
        )

    # Get channel ID from handle
    try:
        search_response = youtube.search().list(
            q=f"@{handle}",
            type="channel",
            part="snippet",
            maxResults=1,
        ).execute()

        if not search_response.get("items"):
            raise ValueError(f"Channel '{handle}' not found")

        channel_id = search_response["items"][0]["snippet"]["channelId"]
        log(f"Found channel ID: {channel_id}")
    except Exception as e:
        raise ValueError(f"Failed to find channel: {e}")

    # Get channel's uploads playlist
    try:
        channel_response = youtube.channels().list(
            id=channel_id,
            part="contentDetails",
        ).execute()

        uploads_playlist_id = channel_response["items"][0]["contentDetails"][
            "relatedPlaylists"
        ]["uploads"]
    except Exception as e:
        raise ValueError(f"Failed to get uploads playlist: {e}")

    # Fetch videos from uploads playlist, sorted by view count
    videos = []
    page_token = None
    items_fetched = 0

    while items_fetched < max_videos:
        playlist_response = youtube.playlistItems().list(
            playlistId=uploads_playlist_id,
            part="snippet,contentDetails",
            maxResults=min(50, max_videos - items_fetched),
            pageToken=page_token,
        ).execute()

        for item in playlist_response.get("items", []):
            video_id = item["contentDetails"]["videoId"]
            title = item["snippet"]["title"]
            published_at = item["snippet"]["publishedAt"]

            # Get view count
            stats = youtube.videos().list(
                id=video_id,
                part="statistics",
            ).execute()

            if stats.get("items"):
                view_count = int(stats["items"][0]["statistics"].get("viewCount", 0))
                videos.append({
                    "video_id": video_id,
                    "title": title,
                    "view_count": view_count,
                    "published_at": published_at,
                    "url": f"https://youtube.com/watch?v={video_id}",
                })
                items_fetched += 1

            if items_fetched >= max_videos:
                break

        page_token = playlist_response.get("nextPageToken")
        if not page_token or items_fetched >= max_videos:
            break

    # Sort by view count descending
    videos.sort(key=lambda v: v["view_count"], reverse=True)
    return videos[:max_videos]


def extract_hooks_from_titles(
    videos: list[dict],
    niche: str,
    provider: Optional[str] = None,
) -> list[dict]:
    """
    Analyze video titles using LLM to extract hook patterns.

    Args:
        videos: List of video dicts with title, view_count, etc.
        niche: Niche name (for context)
        provider: LLM provider (claude, gemini, openai, etc.)

    Returns:
        List of extracted hooks with: template, when, avg_views, source_channel
    """
    if not videos:
        return []

    titles_text = "\n".join(
        [f"- {v['title']} (views: {v['view_count']:,})" for v in videos]
    )

    prompt = f"""You are analyzing top-performing YouTube video titles in the {niche} niche.

These are the most-viewed videos from a successful creator in this space:

{titles_text}

Extract the hook patterns and templates you observe. For each unique hook pattern, provide:

1. A SHORT TEMPLATE (with {{placeholder}} for variables, e.g., "Everyone is celebrating {{topic}}. Here's why that's wrong.")
2. WHEN TO USE (brief guidance on when this hook works best)
3. WHY IT WORKS (the psychological/engagement principle)

Return ONLY a JSON array, no other text. Example format:

[
  {{
    "id": "contrarian_hook",
    "template": "Everyone is celebrating {{topic}}. Here's why...",
    "when": "When the topic has strong positive consensus but has hidden downsides",
    "why_it_works": "Contrasts viewer expectations; creates curiosity gap"
  }},
  {{
    "id": "question_hook",
    "template": "Is {{question}}?",
    "when": "When the answer is surprising or counterintuitive",
    "why_it_works": "Questions activate curiosity and increase watch-through"
  }}
]

Be specific to the {niche} niche. Extract 5-7 unique hook patterns."""

    response = call_llm(prompt, provider=provider)

    # Parse JSON from response
    try:
        # Try to find JSON array in response
        import re

        match = re.search(r"\[.*\]", response, re.DOTALL)
        if match:
            hooks = json.loads(match.group())
        else:
            hooks = json.loads(response)
    except json.JSONDecodeError:
        log(f"Failed to parse hooks JSON: {response}")
        return []

    # Enrich with avg views from videos
    for hook in hooks:
        hook["avg_views"] = sum(v["view_count"] for v in videos) // len(videos)
        hook["extracted_at"] = datetime.utcnow().isoformat()

    return hooks


def merge_learned_hooks(niche_name: str, new_hooks: list[dict]):
    """
    Merge extracted hooks into the niche YAML profile under 'learned_hooks:'.

    Preserves existing hooks and adds/updates learned_hooks section.

    Args:
        niche_name: Name of the niche (e.g., "tech")
        new_hooks: List of hook dicts from extract_hooks_from_titles()
    """
    profile_path = NICHES_DIR / f"{niche_name}.yaml"

    if not profile_path.exists():
        log(f"Niche profile '{niche_name}' not found at {profile_path}")
        return

    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = yaml.safe_load(f) or {}
    except Exception as e:
        log(f"Failed to load niche profile: {e}")
        return

    # Merge learned hooks
    profile["learned_hooks"] = new_hooks

    # Write back to YAML
    try:
        with open(profile_path, "w", encoding="utf-8") as f:
            yaml.dump(profile, f, default_flow_style=False, sort_keys=False)
        log(f"Updated niche profile: {profile_path}")
        log(f"Merged {len(new_hooks)} learned hooks")
    except Exception as e:
        log(f"Failed to write niche profile: {e}")


def analyze_channel(
    channel_url: str,
    niche: str,
    provider: Optional[str] = None,
    max_videos: int = 20,
):
    """
    Full hook analysis pipeline: fetch videos → extract hooks → merge into niche.

    Args:
        channel_url: YouTube channel URL
        niche: Target niche name
        provider: LLM provider
        max_videos: Max videos to analyze
    """
    log(f"Analyzing YouTube channel: {channel_url}")
    log(f"Niche: {niche}")

    try:
        videos = fetch_channel_videos(channel_url, max_videos=max_videos)
        log(f"Fetched {len(videos)} videos")

        for i, v in enumerate(videos[:5], 1):
            log(f"  {i}. {v['title'][:60]}... ({v['view_count']:,} views)")

        hooks = extract_hooks_from_titles(videos, niche, provider=provider)
        log(f"Extracted {len(hooks)} hook patterns")

        for h in hooks:
            log(f"  - {h.get('id', 'unnamed')}: {h.get('template', '')[:60]}...")

        merge_learned_hooks(niche, hooks)
        log(f"✓ Successfully analyzed {channel_url} for niche '{niche}'")

    except Exception as e:
        log(f"✗ Analysis failed: {e}")
        raise
