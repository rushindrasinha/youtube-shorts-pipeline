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
    from .broll import EFFECTS
    effects = EFFECTS  # 8 varied motion effects with micro-jitter

    # Animate each frame with varied Ken Burns effects
    animated = []
    for i, frame in enumerate(frames):
        anim = out_dir / f"anim_{i}.mp4"
        animate_frame(frame, anim, per_frame + 0.1, effects[i % len(effects)])
        animated.append(anim)

    # Merge animated segments with varied transitions
    merged_video = out_dir / "merged_video.mp4"
    xfade_dur = 0.3
    # Rotate through transition types for visual variety
    xfade_types = ["fade", "slideleft", "slideright", "wiperight", "fadeblack", "circleopen"]

    if len(animated) == 1:
        run_cmd(["ffmpeg", "-i", str(animated[0]),
                 "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p",
                 str(merged_video), "-y", "-loglevel", "quiet"])
    else:
        inputs = []
        for a in animated:
            inputs += ["-i", str(a)]

        filter_parts = []
        prev_label = "[0:v]"
        for i in range(1, len(animated)):
            offset = per_frame * i - xfade_dur * i
            out_label = f"[v{i}]" if i < len(animated) - 1 else "[vout]"
            transition = xfade_types[i % len(xfade_types)]
            filter_parts.append(
                f"{prev_label}[{i}:v]xfade=transition={transition}:duration={xfade_dur}:offset={offset:.2f}{out_label}"
            )
            prev_label = out_label

        run_cmd(
            ["ffmpeg"] + inputs +
            ["-filter_complex", ";".join(filter_parts),
             "-map", "[vout]",
             "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p",
             str(merged_video), "-y", "-loglevel", "quiet"]
        )

    # Keep concat _esc for backwards compatibility with state file paths
    def _esc(p):
        s = str(p).replace("'", "'\\''" )
        return s.replace("\n", "").replace("\r", "")

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
            "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p",
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

    # Post-processing: film grain + vignette + warm color grade
    # This removes the "clinically clean AI look"
    post_path = MEDIA_DIR / f"pipeline_{job_id}_{lang}_final.mp4"
    post_vf = ",".join([
        "noise=c0s=6:c0f=t+u",       # subtle film grain (temporal + uniform)
        "vignette=PI/5",               # subtle edge darkening
        "eq=contrast=1.08:saturation=1.12",  # warm contrast boost
    ])
    try:
        run_cmd([
            "ffmpeg", "-i", str(out_path),
            "-vf", post_vf,
            "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            str(post_path), "-y", "-loglevel", "quiet",
        ])
        log(f"Post-processing applied (grain + vignette + color grade)")
        # Replace the output with post-processed version
        post_path.rename(out_path)
    except Exception as e:
        log(f"Post-processing failed: {e} — using unprocessed video")

    log(f"Video assembled: {out_path}")
    return out_path
