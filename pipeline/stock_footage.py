"""Pexels stock video — real footage to mix with AI images."""

from pathlib import Path

import requests

from .config import get_pexels_key, extract_keywords, run_cmd
from .log import log
from .retry import with_retry


@with_retry(max_retries=2, base_delay=2.0)
def _search_pexels_video(query: str, api_key: str) -> dict | None:
    """Search Pexels for a portrait-orientation video matching the query."""
    r = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": api_key},
        params={
            "query": query,
            "orientation": "portrait",
            "size": "medium",
            "per_page": 5,
        },
        timeout=15,
    )
    if r.status_code != 200:
        return None
    videos = r.json().get("videos", [])
    if not videos:
        return None
    # Pick first result with an HD portrait file
    for video in videos:
        for vf in video.get("video_files", []):
            if vf.get("height", 0) >= 1080 and vf.get("width", 0) <= vf.get("height", 0):
                return {"url": vf["link"], "duration": video.get("duration", 10)}
    # Fallback: first video file
    files = videos[0].get("video_files", [])
    if files:
        return {"url": files[0]["link"], "duration": videos[0].get("duration", 10)}
    return None


def fetch_stock_clip(prompt: str, output_path: Path, max_duration: float = 12.0) -> Path | None:
    """Download a stock video clip matching the prompt. Returns path or None."""
    api_key = get_pexels_key()
    if not api_key:
        return None

    keywords = extract_keywords(prompt)
    if not keywords:
        return None

    result = _search_pexels_video(keywords, api_key)
    if not result:
        log(f"No Pexels match for: {keywords}")
        return None

    try:
        r = requests.get(result["url"], timeout=30)
        r.raise_for_status()
        output_path.write_bytes(r.content)
        log(f"Stock clip downloaded: {output_path.name}")

        # Trim to max_duration if needed
        if result["duration"] > max_duration:
            trimmed = output_path.with_name(output_path.stem + "_trimmed.mp4")
            run_cmd([
                "ffmpeg", "-i", str(output_path), "-t", str(max_duration),
                "-c", "copy", str(trimmed), "-y", "-loglevel", "quiet",
            ])
            trimmed.rename(output_path)

        return output_path
    except Exception as e:
        log(f"Stock clip download failed: {e}")
        return None
