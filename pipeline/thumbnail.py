"""Thumbnail generation — Gemini Imagen (16:9) + Pillow text overlay."""

import base64
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from .config import get_gemini_key
from .log import log
from .retry import with_retry

THUMB_WIDTH = 1280
THUMB_HEIGHT = 720


@with_retry(max_retries=3, base_delay=2.0)
def _generate_thumb_image(prompt: str, output_path: Path, api_key: str):
    """Generate a 16:9 thumbnail via Gemini native image generation."""
    url = (
        "https://generativelanguage.googleapis.com/v1beta"
        "/models/gemini-2.0-flash-exp-image-generation:generateContent"
    )
    body = {
        "contents": [{"parts": [{"text": f"Generate a 16:9 landscape image: {prompt}"}]}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
    }
    r = requests.post(
        url, json=body, timeout=90,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
    )
    if r.status_code != 200:
        try:
            detail = r.json().get("error", {}).get("message", r.text[:200])
        except Exception:
            detail = r.text[:200]
        raise RuntimeError(f"Gemini API {r.status_code}: {detail}")

    data = r.json()
    for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        if "inlineData" in part:
            img_b64 = part["inlineData"]["data"]
            output_path.write_bytes(base64.b64decode(img_b64))
            return
    raise RuntimeError("No image in Gemini response")


def _overlay_title(image_path: Path, title: str, output_path: Path):
    """Overlay bold title text with drop shadow on the thumbnail."""
    img = Image.open(image_path).convert("RGB")
    img = img.resize((THUMB_WIDTH, THUMB_HEIGHT), Image.LANCZOS)
    draw = ImageDraw.Draw(img)

    # Try to find a bold font, fall back to default
    font_size = 64
    font = None
    for font_name in [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSDisplay.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        try:
            font = ImageFont.truetype(font_name, font_size)
            break
        except (OSError, IOError):
            continue
    if font is None:
        font = ImageFont.load_default()

    # Word wrap the title
    max_width = THUMB_WIDTH - 80  # 40px padding each side
    lines = _wrap_text(draw, title, font, max_width)
    text_block = "\n".join(lines)

    # Calculate position (center, lower third)
    bbox = draw.multiline_textbbox((0, 0), text_block, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (THUMB_WIDTH - text_w) // 2
    y = THUMB_HEIGHT - text_h - 60  # 60px from bottom

    # Drop shadow
    shadow_offset = 3
    draw.multiline_text(
        (x + shadow_offset, y + shadow_offset),
        text_block, fill=(0, 0, 0), font=font, align="center",
    )

    # Main text
    draw.multiline_text(
        (x, y), text_block, fill=(255, 255, 255), font=font, align="center",
    )

    img.save(output_path)


def _wrap_text(draw: ImageDraw.Draw, text: str, font, max_width: int) -> list[str]:
    """Simple word-wrap for Pillow text rendering."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_thumbnail(draft: dict, out_dir: Path) -> Path:
    """Generate a YouTube thumbnail with Gemini + text overlay.

    Uses the thumbnail_prompt from the draft, overlays the video title.
    Returns path to the final thumbnail PNG.
    """
    api_key = get_gemini_key()
    prompt = draft.get("thumbnail_prompt", "Cinematic YouTube thumbnail")
    title = draft.get("youtube_title", draft.get("news", ""))
    job_id = draft.get("job_id", "unknown")

    raw_path = out_dir / f"thumb_raw_{job_id}.png"
    final_path = out_dir / f"thumb_{job_id}.png"

    log("Generating thumbnail via Gemini Imagen...")
    _generate_thumb_image(prompt, raw_path, api_key)

    log("Adding title overlay...")
    _overlay_title(raw_path, title, final_path)

    log(f"Thumbnail saved: {final_path.name}")
    return final_path
