"""Pexels stock video — real footage to mix with AI images."""

import base64
from pathlib import Path

import requests

from .config import get_pexels_key, get_gemini_key, extract_keywords, run_cmd
from .log import log
from .retry import with_retry


@with_retry(max_retries=2, base_delay=2.0)
def _search_pexels_videos(query: str, api_key: str) -> list[dict]:
    """Search Pexels for portrait-orientation videos. Returns list of candidates."""
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
        return []
    videos = r.json().get("videos", [])
    candidates = []
    for video in videos:
        # Find best video file (HD portrait)
        best_file = None
        for vf in video.get("video_files", []):
            if vf.get("height", 0) >= 1080 and vf.get("width", 0) <= vf.get("height", 0):
                best_file = vf
                break
        if not best_file:
            files = video.get("video_files", [])
            if files:
                best_file = files[0]
        if best_file:
            candidates.append({
                "url": best_file["link"],
                "duration": video.get("duration", 10),
                "image": video.get("image", ""),  # preview thumbnail
            })
    return candidates


def _check_relevance(thumbnail_url: str, prompt: str, gemini_key: str) -> bool:
    """Use Gemini Flash to check if a Pexels thumbnail matches the prompt."""
    try:
        # Download thumbnail
        r = requests.get(thumbnail_url, timeout=10)
        if r.status_code != 200:
            return True  # can't check, assume OK

        img_b64 = base64.b64encode(r.content).decode()

        # Ask Gemini Flash if this matches
        url = (
            "https://generativelanguage.googleapis.com/v1beta"
            "/models/gemini-2.0-flash:generateContent"
        )
        body = {
            "contents": [{
                "parts": [
                    {"inlineData": {"mimeType": "image/jpeg", "data": img_b64}},
                    {"text": (
                        f"I need stock footage for a YouTube Short about finance/crypto. "
                        f"The scene I need is: \"{prompt}\"\n"
                        f"Does this image SPECIFICALLY depict that scene or something visually "
                        f"close enough to use as b-roll? Reject anything that only matches on "
                        f"a pun or unrelated meaning of a word. Answer only YES or NO."
                    )},
                ],
            }],
        }
        resp = requests.post(
            url, json=body, timeout=15,
            headers={"Content-Type": "application/json", "x-goog-api-key": gemini_key},
        )
        if resp.status_code != 200:
            return True  # can't check, assume OK

        text = ""
        for part in resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", []):
            text += part.get("text", "")

        return "YES" in text.upper()
    except Exception:
        return True  # on error, don't block the clip


def fetch_stock_clip(prompt: str, output_path: Path, max_duration: float = 12.0) -> Path | None:
    """Download a relevant stock video clip. Uses Gemini vision to filter bad matches."""
    api_key = get_pexels_key()
    if not api_key:
        return None

    keywords = extract_keywords(prompt)
    if not keywords:
        return None

    candidates = _search_pexels_videos(keywords, api_key)
    if not candidates:
        log(f"No Pexels match for: {keywords}")
        return None

    # Use Gemini to find first relevant candidate
    gemini_key = get_gemini_key()
    picked = None
    for candidate in candidates:
        if gemini_key and candidate.get("image"):
            if _check_relevance(candidate["image"], prompt, gemini_key):
                picked = candidate
                log(f"Pexels clip passed relevance check")
                break
            else:
                log(f"Pexels clip rejected — not relevant")
        else:
            picked = candidate  # no Gemini key, take first result
            break

    if not picked:
        log(f"No relevant Pexels clips for: {keywords}")
        return None

    try:
        r = requests.get(picked["url"], timeout=30)
        r.raise_for_status()
        output_path.write_bytes(r.content)
        log(f"Stock clip downloaded: {output_path.name}")

        # Trim to max_duration if needed
        if picked["duration"] > max_duration:
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
