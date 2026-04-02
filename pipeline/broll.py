"""Gemini Imagen b-roll generation + Ken Burns animation."""

import base64
from pathlib import Path

import requests
from PIL import Image

from .config import VIDEO_WIDTH, VIDEO_HEIGHT, get_gemini_key, run_cmd
from .log import log
from .retry import with_retry


@with_retry(max_retries=3, base_delay=2.0)
def _generate_image_gemini(prompt: str, output_path: Path, api_key: str):
    """Generate image via Gemini native image generation (free tier compatible)."""
    url = (
        "https://generativelanguage.googleapis.com/v1beta"
        "/models/gemini-3.1-flash-image-preview:generateContent"
    )
    body = {
        "contents": [{"parts": [{"text": f"Generate an image: {prompt}"}]}],
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
    # Extract image from response parts
    for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        if "inlineData" in part:
            img_b64 = part["inlineData"]["data"]
            output_path.write_bytes(base64.b64decode(img_b64))
            return
    raise RuntimeError("No image in Gemini response")


def _fallback_frame(i: int, out_dir: Path) -> Path:
    """Solid colour fallback frame if Gemini fails."""
    colors = [(20, 20, 60), (40, 10, 40), (10, 30, 50)]
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), colors[i % len(colors)])
    path = out_dir / f"broll_{i}.png"
    img.save(path)
    return path


_STYLE_SUFFIX = ", 9:16 portrait orientation, photorealistic, cinematic lighting, 4K detail"


def generate_broll(prompts: list, out_dir: Path) -> list[Path]:
    """Generate up to 5 b-roll frames via Gemini Imagen, with fallback."""
    api_key = get_gemini_key()
    frames = []
    max_frames = min(len(prompts), 5)

    for i, prompt in enumerate(prompts[:max_frames]):
        out_path = out_dir / f"broll_{i}.png"
        log(f"Generating b-roll frame {i+1}/{max_frames} via Gemini Imagen...")
        prompt = prompt + _STYLE_SUFFIX

        try:
            _generate_image_gemini(prompt, out_path, api_key)

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

    # Ensure at least 3 frames
    while len(frames) < 3:
        frames.append(_fallback_frame(len(frames), out_dir))

    return frames


# 8 motion effects with sinusoidal micro-jitter for organic camera feel
EFFECTS = [
    "zoom_in", "pan_right", "zoom_out", "pan_left",
    "pan_up", "pan_down", "zoom_in_slow", "drift",
]


def animate_frame(img_path: Path, out_path: Path, duration: float, effect: str = "zoom_in"):
    """Ken Burns animation with micro-jitter for organic camera feel.

    8 effect variants with sinusoidal jitter to break mechanical smoothness.
    """
    fps = 30
    frames = int(duration * fps)
    w, h = VIDEO_WIDTH, VIDEO_HEIGHT

    # All effects include sin()-based micro-jitter on x/y for organic feel.
    # Non-harmonic frequency multipliers (0.06, 0.07, 0.08, 0.09, 0.1, 0.11)
    # prevent obvious looping.
    effect_map = {
        "zoom_in": (
            f"scale={int(w*1.15)}:{int(h*1.15)},"
            f"zoompan=z='1.0+0.12*on/{frames}'"
            f":x='iw/2-(iw/zoom/2)+sin(on*0.07)*8'"
            f":y='ih/2-(ih/zoom/2)+sin(on*0.09)*6'"
            f":d={frames}:s={w}x{h}:fps={fps}"
        ),
        "zoom_out": (
            f"scale={int(w*1.15)}:{int(h*1.15)},"
            f"zoompan=z='1.12-0.12*on/{frames}'"
            f":x='iw/2-(iw/zoom/2)+sin(on*0.06)*7'"
            f":y='ih/2-(ih/zoom/2)+sin(on*0.11)*5'"
            f":d={frames}:s={w}x{h}:fps={fps}"
        ),
        "pan_right": (
            f"scale={int(w*1.2)}:{int(h*1.2)},"
            f"zoompan=z=1.15:x='0.15*iw*on/{frames}+sin(on*0.08)*5'"
            f":y='ih*0.075+sin(on*0.1)*4'"
            f":d={frames}:s={w}x{h}:fps={fps}"
        ),
        "pan_left": (
            f"scale={int(w*1.2)}:{int(h*1.2)},"
            f"zoompan=z=1.15:x='iw*0.15-0.15*iw*on/{frames}+sin(on*0.08)*5'"
            f":y='ih*0.075+sin(on*0.1)*4'"
            f":d={frames}:s={w}x{h}:fps={fps}"
        ),
        "pan_up": (
            f"scale={int(w*1.15)}:{int(h*1.15)},"
            f"zoompan=z=1.1:x='iw*0.05+sin(on*0.07)*6'"
            f":y='ih*0.12-0.12*ih*on/{frames}'"
            f":d={frames}:s={w}x{h}:fps={fps}"
        ),
        "pan_down": (
            f"scale={int(w*1.15)}:{int(h*1.15)},"
            f"zoompan=z=1.1:x='iw*0.05+sin(on*0.07)*6'"
            f":y='0.12*ih*on/{frames}'"
            f":d={frames}:s={w}x{h}:fps={fps}"
        ),
        "zoom_in_slow": (
            f"scale={int(w*1.08)}:{int(h*1.08)},"
            f"zoompan=z='1.0+0.06*on/{frames}'"
            f":x='iw/2-(iw/zoom/2)+sin(on*0.05)*10'"
            f":y='ih/2-(ih/zoom/2)+sin(on*0.07)*8'"
            f":d={frames}:s={w}x{h}:fps={fps}"
        ),
        "drift": (
            f"scale={int(w*1.12)}:{int(h*1.12)},"
            f"zoompan=z='1.05+0.02*sin(on*0.02)'"
            f":x='iw*0.06+sin(on*0.03)*15'"
            f":y='ih*0.06+cos(on*0.025)*12'"
            f":d={frames}:s={w}x{h}:fps={fps}"
        ),
    }

    vf = effect_map.get(effect, effect_map["zoom_in"])

    run_cmd([
        "ffmpeg", "-loop", "1", "-i", str(img_path),
        "-vf", vf, "-t", str(duration), "-r", str(fps),
        "-pix_fmt", "yuv420p", str(out_path), "-y", "-loglevel", "quiet",
    ])
