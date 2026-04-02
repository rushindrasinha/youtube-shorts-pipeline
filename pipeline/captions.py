"""Whisper word-level timestamps + ASS subtitle generation + Pillow fallback."""

from pathlib import Path

from .log import log


def _has_ass_filter() -> bool:
    """Check if ffmpeg has libass (for ASS subtitle burn-in)."""
    import subprocess
    try:
        r = subprocess.run(
            ["ffmpeg", "-filters"],
            capture_output=True, text=True, timeout=5,
        )
        return "ass" in r.stdout
    except Exception:
        return False


def _whisper_word_timestamps(audio_path: Path, lang: str = "en") -> list[dict]:
    """Get word-level timestamps from Whisper.

    Returns list of {"word": str, "start": float, "end": float}.
    """
    try:
        import whisper
    except ImportError:
        log("Whisper not installed — skipping word timestamps")
        return []

    log("Running Whisper for word-level timestamps...")
    model = whisper.load_model("medium")
    result = model.transcribe(
        str(audio_path),
        language=lang[:2],
        word_timestamps=True,
    )

    words = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []):
            words.append({
                "word": w["word"].strip(),
                "start": w["start"],
                "end": w["end"],
            })

    log(f"Got {len(words)} word timestamps.")
    return words


def _group_words(words: list[dict], group_size: int = 3) -> list[list[dict]]:
    """Group words into chunks of group_size for caption display."""
    groups = []
    for i in range(0, len(words), group_size):
        groups.append(words[i:i + group_size])
    return groups


def _format_ass_time(seconds: float) -> str:
    """Format seconds to ASS timestamp: H:MM:SS.cc (centiseconds)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _generate_ass(words: list[dict], output_path: Path, video_width: int = 1080, video_height: int = 1920):
    """Generate ASS subtitle file with word-by-word color highlighting.

    White text for inactive words, yellow for current word.
    Semi-transparent background, positioned at lower third (~70% down).
    """
    # ASS header
    margin_v = int(video_height * 0.25)  # ~75% down from top = 25% from bottom
    header = f"""[Script Info]
Title: Pipeline Captions
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat,78,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,2,0,1,5,0,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    groups = _group_words(words)
    events = []

    for group in groups:
        if not group:
            continue

        group_start = group[0]["start"]
        group_end = group[-1]["end"]

        # For each word in the group being active, emit one dialogue line
        for active_idx, active_word in enumerate(group):
            start = active_word["start"]
            end = active_word["end"]

            # Build text with override tags: green for active, white for rest
            parts = []
            for j, w in enumerate(group):
                # Strip ASS override-tag delimiters to prevent injection
                safe_word = w['word'].replace('{', '').replace('}', '')
                if j == active_idx:
                    # Green highlight, bold, scale pop (110% x/y)
                    parts.append(f"{{\\c&H0008E539&\\b1\\fs88\\fscx110\\fscy110}}{safe_word}{{\\r}}")
                else:
                    parts.append(safe_word)

            text = " ".join(parts)
            events.append(
                f"Dialogue: 0,{_format_ass_time(start)},{_format_ass_time(end)},Default,,0,0,0,,{text}"
            )

    output_path.write_text(header + "\n".join(events), encoding="utf-8")
    log(f"ASS captions saved: {output_path.name}")
    return output_path


def _generate_srt(words: list[dict], output_path: Path) -> Path:
    """Generate standard SRT file from word timestamps."""
    groups = _group_words(words)
    lines = []

    for i, group in enumerate(groups, 1):
        if not group:
            continue
        start = group[0]["start"]
        end = group[-1]["end"]
        text = " ".join(w["word"].replace('{', '').replace('}', '') for w in group)

        start_ts = _srt_time(start)
        end_ts = _srt_time(end)
        lines.append(f"{i}\n{start_ts} --> {end_ts}\n{text}\n")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    log(f"SRT captions saved: {output_path.name}")
    return output_path


def _srt_time(seconds: float) -> str:
    """Format seconds to SRT timestamp: HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _render_remotion_captions(words: list[dict], work_dir: Path) -> Path | None:
    """Render animated TikTok-style captions via Remotion as transparent overlay.

    Returns path to transparent WebM overlay, or None if Remotion unavailable.
    """
    import json as _json
    import shutil
    import subprocess

    if not shutil.which("npx"):
        return None

    remotion_dir = Path(__file__).resolve().parent.parent / "remotion"
    if not (remotion_dir / "node_modules").exists():
        log("Remotion not installed — using ASS captions")
        return None

    # Convert Whisper words to Remotion Caption format
    captions = [
        {
            "text": f" {w['word']}" if i > 0 else w["word"],
            "startMs": int(w["start"] * 1000),
            "endMs": int(w["end"] * 1000),
            "timestampMs": int((w["start"] + w["end"]) / 2 * 1000),
            "confidence": None,
        }
        for i, w in enumerate(words)
    ]
    duration_ms = int(words[-1]["end"] * 1000) + 500 if words else 60000

    # Write captions JSON to Remotion's public/ directory
    captions_file = remotion_dir / "public" / "captions.json"
    captions_file.parent.mkdir(parents=True, exist_ok=True)
    captions_file.write_text(_json.dumps(captions))

    # Write render props
    props = {"captionsJsonFile": "captions.json", "durationMs": duration_ms}
    props_file = work_dir / "remotion_props.json"
    props_file.write_text(_json.dumps(props))

    # Render transparent overlay (ProRes 4444 with alpha channel)
    output = work_dir / "caption_overlay.mov"

    try:
        log("Rendering animated captions via Remotion...")
        subprocess.run(
            [
                "npx", "remotion", "render",
                "src/index.ts", "CaptionOverlay", str(output),
                f"--props={props_file}",
                "--codec=prores",
                "--prores-profile=4444",
                "--image-format=png",
                "--pixel-format=yuva444p10le",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(remotion_dir),
        )
        log(f"Remotion caption overlay rendered: {output.name}")
        return output
    except FileNotFoundError:
        log("npx not found — using ASS captions")
        return None
    except subprocess.TimeoutExpired:
        log("Remotion render timed out — using ASS captions")
        return None
    except Exception as e:
        log(f"Remotion render failed: {e} — using ASS captions")
        return None


def generate_captions(audio_path: Path, work_dir: Path, lang: str = "en") -> dict:
    """Generate captions: ASS (for burn-in) + SRT (for YouTube upload).

    Returns dict with keys: srt_path, ass_path, words (for music ducking).
    """
    words = _whisper_word_timestamps(audio_path, lang)

    result = {"words": words}

    if not words:
        log("No word timestamps — skipping caption generation")
        # Fallback: run whisper CLI for SRT only
        try:
            from .config import run_cmd
            run_cmd([
                "whisper", str(audio_path),
                "--model", "medium",
                "--language", lang[:2],
                "--output_format", "srt",
                "--output_dir", str(work_dir),
            ], capture=True)
            candidates = list(work_dir.glob("*.srt"))
            if candidates:
                srt = candidates[0]
                final = audio_path.with_suffix(".srt")
                srt.rename(final)
                result["srt_path"] = str(final)
        except Exception as e:
            log(f"Whisper CLI fallback failed: {e}")
        return result

    # Generate SRT (always — needed for YouTube upload)
    srt_path = work_dir / f"captions_{lang}.srt"
    _generate_srt(words, srt_path)
    result["srt_path"] = str(srt_path)

    # Try Remotion animated captions first, fall back to ASS
    overlay = _render_remotion_captions(words, work_dir)
    if overlay:
        result["remotion_overlay"] = str(overlay)
    else:
        # ASS burn-in as fallback
        ass_path = work_dir / f"captions_{lang}.ass"
        _generate_ass(words, ass_path)
        result["ass_path"] = str(ass_path)

    return result
