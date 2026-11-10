"""Pollinations b-roll generation + Ken Burns animation."""

import time
import urllib.parse
from pathlib import Path

import requests
from PIL import Image

from .config import VIDEO_WIDTH, VIDEO_HEIGHT, run_cmd
from .log import log
from .retry import with_retry

# Pause between Pollinations requests: the free tier rate-limits
# rapid-fire image generation, so frames are spaced out instead of
# hammering the endpoint.
POLLINATIONS_RATE_LIMIT_DELAY_S = 16


@with_retry(max_retries=3, base_delay=2.0)
def _generate_image_pollinations(prompt: str, output_path: Path):
    """Generate an image via Pollinations.ai — free, no API key needed."""
    encoded_prompt = urllib.parse.quote(prompt, safe="")
    url = (
        f"https://image.pollinations.ai/prompt/{encoded_prompt}"
        "?width=1080&height=1920&nologo=true"
    )
    r = requests.get(url, timeout=90)
    if r.status_code != 200:
        raise RuntimeError(
            f"Pollinations API {r.status_code}: {r.text[:200]}"
        )
    content_type = r.headers.get("Content-Type", "")
    if content_type and not content_type.startswith("image/"):
        raise RuntimeError(
            f"Pollinations returned non-image content "
            f"({content_type}): {r.text[:200]}"
        )
    output_path.write_bytes(r.content)
    time.sleep(POLLINATIONS_RATE_LIMIT_DELAY_S)


def _fallback_frame(i: int, out_dir: Path) -> Path:
    """Solid colour fallback frame if image generation fails."""
    colors = [(20, 20, 60), (40, 10, 40), (10, 30, 50)]
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), colors[i % len(colors)])
    path = out_dir / f"broll_{i}.png"
    img.save(path)
    return path


def generate_broll(prompts: list, out_dir: Path) -> list[Path]:
    """Generate 3 b-roll frames via Pollinations, with fallback.

    Pollinations is free with no API key, so no key is required —
    a frame that fails to generate falls back to a solid-colour frame.
    """
    frames = []

    for i, prompt in enumerate(prompts[:3]):
        out_path = out_dir / f"broll_{i}.png"
        log(f"Generating b-roll frame {i+1}/3 via Pollinations...")

        try:
            _generate_image_pollinations(prompt, out_path)

            # Resize/crop to 9:16 portrait
            img = Image.open(out_path).convert("RGB")
            target_w, target_h = VIDEO_WIDTH, VIDEO_HEIGHT
            orig_w, orig_h = img.size
            scale = max(target_w / orig_w, target_h / orig_h)
            new_w, new_h = int(orig_w * scale), int(orig_h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            left = (new_w - target_w) // 2
            top = (new_h - target_h) // 2
            img = img.crop((left, top, left + target_w, top + target_h))
            img.save(out_path)
            frames.append(out_path)

        except Exception as e:
            log(f"Frame {i+1} failed: {e} — using fallback")
            frames.append(_fallback_frame(i, out_dir))

    return frames


def animate_frame(img_path: Path, out_path: Path, duration: float, effect: str = "zoom_in"):
    """Ken Burns animation on a single frame."""
    fps = 30
    frames = int(duration * fps)
    w, h = VIDEO_WIDTH, VIDEO_HEIGHT

    if effect == "zoom_in":
        vf = (
            f"scale={int(w * 1.12)}:{int(h * 1.12)},"
            f"zoompan=z='1.12-0.12*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={w}x{h}:fps={fps}"
        )
    elif effect == "pan_right":
        vf = (
            f"scale={int(w * 1.15)}:{int(h * 1.15)},"
            f"zoompan=z=1.15:x='0.15*iw*on/{frames}':y='ih*0.075'"
            f":d={frames}:s={w}x{h}:fps={fps}"
        )
    else:  # zoom_out
        vf = (
            f"scale={int(w * 1.12)}:{int(h * 1.12)},"
            f"zoompan=z='1.0+0.12*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={w}x{h}:fps={fps}"
        )

    run_cmd([
        "ffmpeg", "-loop", "1", "-i", str(img_path),
        "-vf", vf, "-t", str(duration), "-r", str(fps),
        "-pix_fmt", "yuv420p", str(out_path), "-y", "-loglevel", "quiet",
    ])
