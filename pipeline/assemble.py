"""ffmpeg video assembly — frames + voiceover + music + captions."""

import re
from pathlib import Path

from .broll import animate_frame
from .config import MEDIA_DIR, run_cmd
from .log import log

# Allowlist for duck_filter values — matches output of music.build_duck_filter()
# e.g. "volume=0.50" or "volume='if(between(t,0.30,1.50)+between(t,2.00,3.50), 0.25, 0.50)':eval=frame"
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
    remotion_overlay: str | None = None,
    words: list[dict] | None = None,
    script: str | None = None,
    mood: str | None = None,
    broll_prompts: list[str] | None = None,
) -> Path:
    """Assemble final video from frames, voiceover, captions, and music."""
    log("Assembling video...")
    if not frames:
        raise ValueError("No b-roll frames provided — cannot assemble video")
    duration = get_audio_duration(voiceover)
    from .broll import EFFECTS
    effects = EFFECTS  # 8 varied motion effects with micro-jitter

    # Vary frame durations — hook is shorter, middle varies, end holds
    n = len(frames)
    if n <= 2:
        per_frame_list = [duration / n] * n
    else:
        avg = duration / n
        weights = []
        for i in range(n):
            if i == 0:
                weights.append(0.6)   # Hook — fast
            elif i == n - 1:
                weights.append(1.3)   # End — holds longer
            elif i < n // 2:
                weights.append(0.9)   # Early body — slightly fast
            else:
                weights.append(1.1)   # Late body — slightly slow
        total_weight = sum(weights)
        per_frame_list = [duration * w / total_weight for w in weights]

    per_frame = sum(per_frame_list) / len(per_frame_list)  # average for backward compat

    # Animate each frame — Veo 3.1 Lite video gen with Ken Burns fallback
    animated = []
    prompts = broll_prompts or []
    for i, frame in enumerate(frames):
        anim = out_dir / f"anim_{i}.mp4"
        frame_dur = per_frame_list[i] if i < len(per_frame_list) else per_frame
        frame_prompt = prompts[i] if i < len(prompts) else None
        animate_frame(frame, anim, frame_dur + 0.1, effects[i % len(effects)],
                      prompt=frame_prompt)
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

        # Compute cumulative offsets from ACTUAL clip durations (not planned)
        # Veo clips may differ from planned durations due to API constraints
        actual_durs = []
        for a in animated:
            try:
                r = run_cmd(
                    ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                     "-of", "csv=p=0", str(a)],
                    capture=True,
                )
                actual_durs.append(float(r.stdout.strip()))
            except Exception:
                actual_durs.append(per_frame_list[len(actual_durs)] if len(actual_durs) < len(per_frame_list) else per_frame)

        cumulative = [0.0]
        for d in actual_durs:
            cumulative.append(cumulative[-1] + d)

        filter_parts = []
        prev_label = "[0:v]"
        for i in range(1, len(animated)):
            offset = cumulative[i] - xfade_dur * i
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

    # Determine caption method: Remotion overlay (animated) or ASS burn-in (fallback)
    use_remotion_overlay = remotion_overlay and Path(remotion_overlay).exists()

    vf_parts = []
    if not use_remotion_overlay and ass_path and Path(ass_path).exists():
        # ASS burn-in fallback — escape all ffmpeg filter-graph special characters
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
                duck_filter = "volume=0.50"
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

    # Composite Remotion animated caption overlay (if available)
    if use_remotion_overlay:
        composited = out_dir / "composited.mp4"
        try:
            run_cmd([
                "ffmpeg",
                "-i", str(out_path),
                "-i", str(remotion_overlay),
                "-filter_complex", "[0:v][1:v]overlay=0:0:shortest=1[vout]",
                "-map", "[vout]", "-map", "0:a",
                "-c:v", "libx264", "-preset", "medium", "-pix_fmt", "yuv420p",
                "-c:a", "copy",
                str(composited), "-y", "-loglevel", "quiet",
            ])
            log("Remotion animated captions composited")
            composited.rename(out_path)
        except Exception as e:
            log(f"Remotion composite failed: {e} — captions may be missing")

    # SFX layer — whooshes at transitions, impacts on emphasis words
    try:
        from .sfx import generate_sfx_set, plan_sfx_placement, mix_sfx_track
        # Use cumulative durations for transition timestamps
        cum = [0.0]
        for d in per_frame_list:
            cum.append(cum[-1] + d)
        transition_times = cum[1:-1]  # transitions between frames (not at start/end)
        sfx_placements = plan_sfx_placement(words or [], transition_times, script or "")
        if sfx_placements:
            sfx_set = generate_sfx_set(out_dir)
            sfx_track = out_dir / "sfx_mixed.mp3"
            sfx_result = mix_sfx_track(sfx_placements, sfx_set, duration, sfx_track)
            if sfx_result and sfx_result.exists():
                # Mix SFX track into the assembled video
                sfx_out = out_dir / "with_sfx.mp4"
                run_cmd([
                    "ffmpeg", "-i", str(out_path), "-i", str(sfx_result),
                    "-filter_complex",
                    "[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=2[aout]",
                    "-map", "0:v", "-map", "[aout]",
                    "-c:v", "copy", "-c:a", "aac",
                    str(sfx_out), "-y", "-loglevel", "quiet",
                ])
                sfx_out.rename(out_path)
                log("SFX layer mixed into video")
    except Exception as e:
        log(f"SFX mixing failed: {e} — continuing without SFX")

    # Post-processing: color grade + film grain + vignette
    # This removes the "clinically clean AI look"
    post_path = MEDIA_DIR / f"pipeline_{job_id}_{lang}_final.mp4"

    # Mood-matched color grading (inline filters — no .cube LUT files needed)
    mood_grade = {
        "tech":  "colorbalance=rs=-0.08:gs=0.02:bs=0.08:rm=-0.05:gm=0.01:bm=0.06",
        "dark":  "colorbalance=rs=-0.03:gs=-0.03:bs=0.03:rh=-0.02:gh=-0.02:bh=0.04",
        "hype":  "colorbalance=rs=0.05:gs=-0.01:bs=-0.05:rm=0.04:bm=-0.03",
        "uplifting": "colorbalance=rs=0.06:gs=0.02:bs=-0.04:rh=0.03:gh=0.01:bh=-0.02",
    }
    grade_filter = mood_grade.get(mood or "", "colorbalance=rs=0.05:gs=0.01:bs=-0.04")

    post_vf_parts = [
        grade_filter,                  # mood-matched color grade
        "noise=c0s=6:c0f=t+u",        # subtle film grain (temporal + uniform)
        "vignette=PI/5",               # subtle edge darkening
        "eq=contrast=1.08:saturation=1.12",  # warm contrast boost
    ]

    post_vf = ",".join(post_vf_parts)
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
