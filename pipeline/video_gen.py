"""Veo 3.1 Lite image-to-video — real motion from still frames."""

import time
from pathlib import Path

from .config import get_gemini_key
from .log import log
from .retry import with_retry

# Polling config
_POLL_INTERVAL = 10  # seconds between status checks
_MAX_POLL_TIME = 300  # 5 minutes max wait


@with_retry(max_retries=1, base_delay=5.0)
def generate_video_from_image(
    image_path: Path,
    prompt: str,
    output_path: Path,
    duration_seconds: int = 5,
) -> Path:
    """Generate a video clip from a still image using Google Veo 3.1 Lite.

    Takes an AI-generated image and produces a short video with real motion,
    camera movement, and physics. Falls back to None on failure (caller
    should use Ken Burns fallback).
    """
    from google import genai
    from google.genai import types

    api_key = get_gemini_key()
    if not api_key:
        raise RuntimeError("No GEMINI_API_KEY configured")

    client = genai.Client(api_key=api_key)

    # Load image
    image_bytes = image_path.read_bytes()
    mime = "image/png" if image_path.suffix == ".png" else "image/jpeg"
    image = types.Image(mimeType=mime, imageBytes=image_bytes)

    # Clamp duration to valid Veo Lite values (even only: 4, 6, 8)
    valid_durations = [4, 6, 8]
    duration = min(valid_durations, key=lambda x: abs(x - duration_seconds))

    log(f"Generating video from {image_path.name} via Veo 3.1 Lite ({duration}s)...")

    operation = client.models.generate_videos(
        model="veo-3.1-lite-generate-preview",
        prompt=prompt,
        image=image,
        config=types.GenerateVideosConfig(
            aspectRatio="9:16",
            durationSeconds=duration,
            resolution="720p",
        ),
    )

    # Poll for completion
    elapsed = 0
    while not operation.done:
        if elapsed >= _MAX_POLL_TIME:
            raise RuntimeError(f"Veo generation timed out after {_MAX_POLL_TIME}s")
        time.sleep(_POLL_INTERVAL)
        elapsed += _POLL_INTERVAL
        operation = client.operations.get(operation)

    # Download the generated video
    video = operation.response.generated_videos[0]
    client.files.download(file=video.video)
    video.video.save(str(output_path))

    log(f"Veo video generated: {output_path.name} ({elapsed}s)")
    return output_path
