"""Multi-platform distribution via the Upload-Post API.

`upload.py` publishes to YouTube through the YouTube Data API, which needs its own
OAuth client and — until the project passes Google's audit — force-locks every
uploaded video to `private`. It also only ever reaches YouTube, even though the
pipeline already drafts a TikTok-shaped script and an Instagram caption.

This module sends the same rendered vertical video to TikTok, Instagram Reels,
YouTube Shorts and the rest through Upload-Post (https://upload-post.com): one API
key, one HTTP request, no per-platform OAuth client to register and maintain.

Docs: https://docs.upload-post.com
"""

from pathlib import Path

import requests

from .config import get_uploadpost_key, get_uploadpost_user
from .log import log
from .retry import with_retry

API_BASE = "https://api.upload-post.com"

SUPPORTED_PLATFORMS = (
    "tiktok",
    "instagram",
    "youtube",
    "facebook",
    "linkedin",
    "x",
    "threads",
    "pinterest",
    "bluesky",
    "reddit",
    "telegram",
    "discord",
    "google_business",
)

# Platforms that reject an upload without a title.
TITLE_REQUIRED_PLATFORMS = ("youtube", "reddit")

# Draft fields the pipeline already produces, mapped to per-platform overrides.
DRAFT_TITLE_FIELDS = {
    "instagram": "instagram_caption",
    "tiktok": "tiktok_caption",
    "youtube": "youtube_title",
}


def is_configured() -> bool:
    """True when an Upload-Post API key and profile are available."""
    return bool(get_uploadpost_key() and get_uploadpost_user())


def parse_platforms(raw: str) -> list[str]:
    """Parse and validate a comma-separated platform list."""
    platforms = [p.strip().lower() for p in (raw or "").split(",") if p.strip()]
    unknown = [p for p in platforms if p not in SUPPORTED_PLATFORMS]
    if unknown:
        raise ValueError(
            f"Unsupported platform(s): {', '.join(unknown)}. "
            f"Supported: {', '.join(SUPPORTED_PLATFORMS)}"
        )
    return platforms


def build_payload(draft: dict, platforms: list[str], user: str) -> dict:
    """Map the draft metadata onto Upload-Post form fields."""
    title = draft.get("youtube_title") or draft.get("news") or ""

    payload = {
        "user": user,
        "title": title[:2200],
        "platform[]": platforms,
        "async_upload": "true",
    }

    description = draft.get("youtube_description")
    if description:
        payload["description"] = description

    # Reuse the per-platform copy the drafting stage already writes
    for platform in platforms:
        field = DRAFT_TITLE_FIELDS.get(platform)
        value = draft.get(field) if field else None
        if value and value != title:
            payload[f"{platform}_title"] = value

    return payload


class DistributionError(RuntimeError):
    """Upload-Post rejected the request. Not worth retrying."""


@with_retry(max_retries=2, base_delay=5.0)
def _post_video(video_path: Path, payload: dict, api_key: str) -> dict:
    """POST the video. Only transient failures reach the retry decorator."""
    with open(video_path, "rb") as video:
        response = requests.post(
            f"{API_BASE}/api/upload",
            # Upload-Post API keys use the Apikey scheme — Bearer returns a misleading 401
            headers={"Authorization": f"Apikey {api_key}"},
            data=payload,
            files={"video": (video_path.name, video, "video/mp4")},
            timeout=600,
        )

    try:
        result = response.json()
    except ValueError:
        message = f"Upload-Post returned a non-JSON response ({response.status_code}): {response.text[:200]}"
        # 5xx is worth another attempt; anything else is not
        raise RuntimeError(message) if response.status_code >= 500 else DistributionError(message)

    if response.status_code >= 400 or result.get("success") is False:
        message = result.get("message") or result.get("error") or response.text[:200]
        message = f"Distribution failed ({response.status_code}): {message}"
        # 4xx means bad key/params — retrying only wastes time
        raise RuntimeError(message) if response.status_code >= 500 else DistributionError(message)

    return result


def publish_to_platforms(
    video_path: Path,
    draft: dict,
    platforms: list[str],
    scheduled_date: str = None,
    timezone: str = None,
) -> dict:
    """Publish one rendered video to several platforms in a single request.

    Args:
        video_path: The rendered vertical video
        draft: Draft dict, used for titles/description
        platforms: Target platforms (see SUPPORTED_PLATFORMS)
        scheduled_date: Optional ISO-8601 timestamp to schedule instead of publishing now
        timezone: Optional IANA timezone for `scheduled_date` (defaults to UTC)

    Returns:
        The Upload-Post response, including a `request_id` for status polling.

    Every argument is validated before the network call, so a bad platform or a
    missing file fails immediately instead of going through the retry backoff.
    """
    api_key = get_uploadpost_key()
    user = get_uploadpost_user()
    if not api_key or not user:
        raise RuntimeError(
            "Upload-Post is not configured.\n"
            "Set UPLOADPOST_API_KEY and UPLOADPOST_USER (env or ~/.verticals/config.json).\n"
            "Get them at https://upload-post.com"
        )

    if not platforms:
        raise ValueError("No target platforms given")

    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    payload = build_payload(draft, platforms, user)
    if not payload["title"].strip() and any(p in TITLE_REQUIRED_PLATFORMS for p in platforms):
        raise ValueError(f"A title is required for {', '.join(TITLE_REQUIRED_PLATFORMS)}")

    if scheduled_date:
        payload["scheduled_date"] = scheduled_date
        if timezone:
            payload["timezone"] = timezone

    log(f"Distributing {video_path.name} to {', '.join(platforms)}...")

    result = _post_video(video_path, payload, api_key)

    request_id = result.get("request_id")
    if scheduled_date:
        log(f"Scheduled for {scheduled_date} (request_id={request_id})")
    else:
        log(f"Submitted (request_id={request_id})")
    return result


def check_status(request_id: str) -> dict:
    """Poll the per-platform result of a previous distribution."""
    api_key = get_uploadpost_key()
    if not api_key:
        raise RuntimeError("Upload-Post is not configured")

    response = requests.get(
        f"{API_BASE}/api/uploadposts/status",
        headers={"Authorization": f"Apikey {api_key}"},
        params={"request_id": request_id},
        timeout=30,
    )
    try:
        return response.json()
    except ValueError:
        return {"success": False, "message": response.text[:200]}
