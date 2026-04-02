"""ffmpeg video assembly — frames + voiceover + music + captions."""

import re
from pathlib import Path

from .broll import animate_frame
from .config import MEDIA_DIR, run_cmd
from .log import log

# Allowlist for duck_filter values — matches output of music.build_duck_filter()
# e.g. "volume=0.25" or "volume='if(between(t,0.30,1.50)+between(t,2.00,3.50), 0.12, 0.25)':eval=frame"
_DUCK_FILTER_RE = re.compile(
    r"^volume=['\"]?[a-zA-Z0-9_()+.,/:' ]*['\"]?(?::eval=frame)?$"
)


def get_audio_duration(path: Path) -> float:
    """Get duration of an audio file in seconds."""
    r = run_cmd(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture=True,
    )
    return float(r.stdout.strip())


def assemble_video(
    frames: list[Path],
    voiceover: Path,
    out_dir: Path,
    job_id: str,
    lang: str = "en",
    ass_path: str | None = None,
    music_path: str | None = None,
    duck_filter: str | None = None,
) -> Path:
    """Assemble final video from frames, voiceover, captions, and music."""
    log("Assembling video...")
    if not frames:
        raise ValueError("No b-roll frames provided — cannot assemble video")
    duration = get_audio_duration(voiceover)
    per_frame = duration / len(frames)
    effects = ["zoom_in", "pan_right", "zoom_out"]

    # Animate each frame with Ken Burns effect
    animated = []
    for i, frame in enumerate(frames):
        anim = out_dir / f"anim_{i}.mp4"
        animate_frame(frame, anim, per_frame + 0.1, effects[i % len(effects)])
        animated.append(anim)

    # Concat animated segments (escape single quotes for ffmpeg concat demuxer)
    concat_file = out_dir / "concat.txt"
    def _esc(p):
        s = str(p).replace("'", "'\\''" )
        return s.replace("\n", "").replace("\r", "")
    concat_file.write_text("\n".join(f"file '{_esc(p)}'" for p in animated))

    merged_video = out_dir / "merged_video.mp4"
    run_cmd([
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        str(merged_video), "-y", "-loglevel", "quiet",
    ])

    # Build the final ffmpeg command with optional captions + music
    out_path = MEDIA_DIR / f"pipeline_{job_id}_{lang}.mp4"

    # Determine video filter (captions via ASS)
    vf_parts = []
    if ass_path and Path(ass_path).exists():
        # Escape special chars in path for ffmpeg filter
        # Escape all ffmpeg filter-graph special characters in the ASS path
        escaped_ass = (str(ass_path)
                       .replace("\\", "\\\\")
                       .replace(":", "\\:")
                       .replace("'", "\\'")
                       .replace(";", "\\;")
                       .replace("[", "\\[")
                       .replace("]", "\\]")
                       .replace(",", "\\,"))
        vf_parts.append(f"ass={escaped_ass}")
    vf = ",".join(vf_parts) if vf_parts else None

    if music_path and Path(music_path).exists():
        # Three inputs: video, voiceover, music
        cmd = ["ffmpeg", "-i", str(merged_video), "-i", str(voiceover)]

        # Loop music to match video duration, apply ducking
        music_filter = f"[2:a]aloop=loop=-1:size=2e+09,atrim=0:{duration}"
        if duck_filter:
            # Validate duck_filter against allowlist (state file tamper defence)
            if not _DUCK_FILTER_RE.match(duck_filter):
                log(f"Invalid duck_filter rejected: {duck_filter[:80]!r}")
                duck_filter = "volume=0.25"
            music_filter += f",{duck_filter}"
        music_filter += "[music]"

        # Mix voiceover + ducked music
        audio_filter = f"{music_filter};[1:a][music]amix=inputs=2:duration=first:dropout_transition=2[aout]"

        cmd += [
            "-stream_loop", "-1", "-i", str(music_path),
            "-filter_complex", audio_filter,
        ]

        if vf:
            cmd += ["-vf", vf]

        cmd += [
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            str(out_path), "-y", "-loglevel", "quiet",
        ]
    else:
        # Two inputs: video + voiceover (no music)
        cmd = ["ffmpeg", "-i", str(merged_video), "-i", str(voiceover)]

        if vf:
            cmd += ["-vf", vf]

        cmd += [
            "-c:v", "libx264" if vf else "copy",
            "-c:a", "aac", "-shortest",
            str(out_path), "-y", "-loglevel", "quiet",
        ]

    run_cmd(cmd)
    log(f"Video assembled: {out_path}")
    return out_path
