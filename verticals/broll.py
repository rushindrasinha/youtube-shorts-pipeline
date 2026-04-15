"""Gemini Imagen b-roll generation + Pexels fallback + Ken Burns animation."""

import base64
import os
from pathlib import Path

import requests
from PIL import Image

from .api_client import get_client
from .config import VIDEO_WIDTH, VIDEO_HEIGHT, get_gemini_key, run_cmd
from .fallback import FallbackChain
from .log import log
from .retry import with_retry


@with_retry(max_retries=3, base_delay=2.0)
def _generate_image_gemini(prompt: str, output_path: Path, api_key: str):
    """Generate image via Imagen 4 (fast) — free tier compatible."""
    # Try Imagen 4 fast first, fall back to gemini-2.5-flash-image
    for model, body_fn in [
        (
            "imagen-4.0-fast-generate-001",
            lambda p: {
                "instances": [{"prompt": p}],
                "parameters": {"sampleCount": 1, "aspectRatio": "9:16"},
            },
        ),
        (
            "gemini-2.5-flash-image",
            lambda p: {
                "contents": [{"parts": [{"text": f"Generate a photorealistic image: {p}"}]}],
                "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
            },
        ),
    ]:
        try:
            if "imagen" in model:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta"
                    f"/models/{model}:predict"
                )
                r = requests.post(
                    url, json=body_fn(prompt), timeout=90,
                    headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                )
                if r.status_code == 200:
                    predictions = r.json().get("predictions", [])
                    if predictions:
                        img_b64 = predictions[0].get("bytesBase64Encoded", "")
                        if img_b64:
                            output_path.write_bytes(base64.b64decode(img_b64))
                            return
            else:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta"
                    f"/models/{model}:generateContent"
                )
                r = requests.post(
                    url, json=body_fn(prompt), timeout=90,
                    headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
                )
                if r.status_code == 200:
                    for part in r.json().get("candidates", [{}])[0].get("content", {}).get("parts", []):
                        if "inlineData" in part:
                            output_path.write_bytes(base64.b64decode(part["inlineData"]["data"]))
                            return
            try:
                detail = r.json().get("error", {}).get("message", r.text[:200])
            except Exception:
                detail = r.text[:200]
            log(f"Model {model} failed ({r.status_code}): {detail} — trying next")
        except Exception as e:
            log(f"Model {model} error: {e} — trying next")
    raise RuntimeError("All Gemini image models failed")


def _load_custom_footage(topic: str, niche: str, output_path: Path, i: int) -> bool:
    """Search user's custom footage directory for story-matching clips.

    Returns True if successful, False otherwise.
    """
    custom_dir = Path.home() / "custom_footage" / niche
    if not custom_dir.exists():
        return False

    try:
        # Extract topic keywords (e.g., "cheating", "revenge", "workplace")
        keywords = topic.lower().split()[:3]

        # Search subdirectories matching keywords
        for subdir in custom_dir.iterdir():
            if subdir.is_dir() and any(k in subdir.name.lower() for k in keywords):
                # Find first video/image in matching subdirectory
                for media_file in sorted(subdir.glob("*")):
                    if media_file.suffix.lower() in [".mp4", ".mov", ".jpg", ".png"]:
                        if media_file.suffix.lower() in [".mp4", ".mov"]:
                            # Extract frame from video
                            cmd = [
                                "ffmpeg", "-i", str(media_file),
                                "-ss", "00:00:01", "-vframes", "1",
                                "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2",
                                str(output_path), "-y", "-loglevel", "quiet",
                            ]
                            run_cmd(cmd)
                        else:
                            # Use image directly
                            img = Image.open(media_file).convert("RGB")
                            target_w, target_h = VIDEO_WIDTH, VIDEO_HEIGHT
                            orig_w, orig_h = img.size
                            scale = max(target_w / orig_w, target_h / orig_h)
                            new_w, new_h = int(orig_w * scale), int(orig_h * scale)
                            img = img.resize((new_w, new_h), Image.LANCZOS)
                            left = (new_w - target_w) // 2
                            top = (new_h - target_h) // 2
                            img = img.crop((left, top, left + target_w, top + target_h))
                            img.save(output_path)
                        return True
        return False
    except Exception as e:
        log(f"Custom footage search failed: {e}")
        return False


def _get_pexels_frame(topic: str, niche: str, output_path: Path, i: int) -> bool:
    """Search Pexels for a video matching the story topic and extract a frame.

    Returns True if successful, False otherwise.
    """
    api_key = os.environ.get("PEXELS_API_KEY", "")
    if not api_key:
        return False

    try:
        # Use story topic for keyword search (not generic prompt)
        keywords = topic

        try:
            data = get_client().get_json(
                "https://api.pexels.com/videos/search",
                params={"query": keywords, "per_page": 1, "orientation": "portrait"},
                headers={"Authorization": api_key},
                timeout=10,
            )
        except RuntimeError:
            return False

        videos = data.get("videos", [])
        if not videos:
            return False

        video = videos[0]
        video_files = video.get("video_files", [])
        if not video_files:
            return False

        # Get highest quality file (usually last in list)
        video_file = video_files[-1]
        video_url = video_file.get("link", "")
        if not video_url:
            return False

        # Download video
        video_path = output_path.parent / f"pexels_{i}.mp4"
        r = requests.get(video_url, timeout=30)
        if r.status_code != 200:
            return False
        video_path.write_bytes(r.content)

        # Extract frame from middle of video
        cmd = [
            "ffmpeg", "-i", str(video_path),
            "-ss", "00:00:01", "-vframes", "1",
            "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2",
            str(output_path), "-y", "-loglevel", "quiet",
        ]
        run_cmd(cmd)
        video_path.unlink()  # Clean up temp video
        return True
    except Exception as e:
        log(f"Pexels frame extraction failed: {e}")
        return False


def _fallback_frame(i: int, out_dir: Path) -> Path:
    """Solid colour fallback frame if Gemini fails."""
    colors = [(20, 20, 60), (40, 10, 40), (10, 30, 50)]
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), colors[i % len(colors)])
    path = out_dir / f"broll_{i}.png"
    img.save(path)
    return path


def generate_broll(prompts: list, out_dir: Path, topic: str = "", niche: str = "") -> list[Path]:
    """Generate 3 b-roll frames: custom footage → Gemini → Pexels → solid color fallback."""
    api_key = get_gemini_key()
    frames = []

    def _gemini_and_resize(prompt: str, out_path: Path) -> Path:
        _generate_image_gemini(prompt, out_path, api_key)
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
        return out_path

    for i, prompt in enumerate(prompts[:3]):
        out_path = out_dir / f"broll_{i}.png"
        log(f"Generating b-roll frame {i+1}/3...")

        def _try_custom(i=i, out_path=out_path):
            if not (topic and niche):
                raise RuntimeError("no topic/niche for custom footage")
            log(f"Searching custom footage for '{topic}' in {niche}...")
            if _load_custom_footage(topic, niche, out_path, i):
                return out_path
            raise RuntimeError("custom footage not found")

        def _try_pexels(i=i, out_path=out_path):
            if not (topic and niche):
                raise RuntimeError("no topic/niche for Pexels")
            if _get_pexels_frame(topic, niche, out_path, i):
                return out_path
            raise RuntimeError("Pexels returned no frames")

        frame = (
            FallbackChain(f"broll_{i}")
            .add("custom", _try_custom)
            .add("gemini", lambda p=prompt, o=out_path: _gemini_and_resize(p, o))
            .add("pexels", _try_pexels)
            .add("solid_color", lambda i=i: _fallback_frame(i, out_dir))
            .execute()
        )
        frames.append(frame)

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
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-pix_fmt", "yuv420p", "-y",
        str(out_path), "-loglevel", "quiet",
    ])
