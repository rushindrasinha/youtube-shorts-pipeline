"""Sound effects — whooshes at transitions, impacts on emphasis words."""

from pathlib import Path

from .config import get_elevenlabs_key, run_cmd
from .log import log


# Pre-bundled SFX prompts for ElevenLabs Sound Effects API
SFX_PROMPTS = {
    "whoosh": "quick cinematic whoosh, single swoosh sound, short",
    "impact": "deep sub bass impact hit, short and punchy",
    "bass_drop": "heavy bass drop, dramatic sub boom",
    "ping": "soft digital notification ping, gentle bell tone",
    "riser": "rising synth tension build, 2 seconds, increasing pitch",
}


def _generate_sfx_elevenlabs(prompt: str, output_path: Path, api_key: str) -> Path | None:
    """Generate a sound effect via ElevenLabs Sound Effects API."""
    import requests
    try:
        r = requests.post(
            "https://api.elevenlabs.io/v1/sound-generation",
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json={"text": prompt, "duration_seconds": 1.5},
            timeout=30,
        )
        if r.status_code == 200:
            output_path.write_bytes(r.content)
            return output_path
    except Exception:
        pass
    return None


def _generate_sfx_ffmpeg(sfx_type: str, output_path: Path) -> Path:
    """Generate SFX using ffmpeg synthesis (fallback)."""
    if sfx_type == "whoosh":
        run_cmd([
            "ffmpeg", "-f", "lavfi", "-i",
            "aevalsrc='0.3*sin(2*PI*(200+3800*t/0.4)*t)*exp(-3*t/0.4)':d=0.4:s=48000",
            "-af", "afade=t=in:d=0.05,afade=t=out:d=0.15:st=0.25",
            str(output_path), "-y", "-loglevel", "quiet",
        ])
    elif sfx_type == "impact":
        run_cmd([
            "ffmpeg", "-f", "lavfi", "-i",
            "aevalsrc='0.5*sin(2*PI*(120-80*t/0.5)*t)*exp(-5*t/0.5)':d=0.5:s=48000",
            "-af", "lowpass=f=200,afade=t=in:d=0.02",
            str(output_path), "-y", "-loglevel", "quiet",
        ])
    elif sfx_type == "ping":
        run_cmd([
            "ffmpeg", "-f", "lavfi", "-i",
            "aevalsrc='0.2*sin(2*PI*880*t)*exp(-15*t)+0.15*sin(2*PI*1320*t)*exp(-12*t)':d=0.15:s=48000",
            "-af", "afade=t=out:d=0.1:st=0.05",
            str(output_path), "-y", "-loglevel", "quiet",
        ])
    else:  # bass_drop or riser
        run_cmd([
            "ffmpeg", "-f", "lavfi", "-i",
            "aevalsrc='0.4*sin(2*PI*60*t)*exp(-4*t/0.6)':d=0.6:s=48000",
            str(output_path), "-y", "-loglevel", "quiet",
        ])
    return output_path


def generate_sfx_set(work_dir: Path) -> dict[str, Path]:
    """Generate a set of SFX files (ElevenLabs or ffmpeg fallback)."""
    api_key = get_elevenlabs_key()
    sfx_dir = work_dir / "sfx"
    sfx_dir.mkdir(exist_ok=True)
    result = {}

    for name, prompt in SFX_PROMPTS.items():
        out = sfx_dir / f"{name}.mp3"
        if out.exists():
            result[name] = out
            continue
        if api_key:
            generated = _generate_sfx_elevenlabs(prompt, out, api_key)
            if generated:
                result[name] = generated
                continue
        # Fallback to ffmpeg synthesis
        result[name] = _generate_sfx_ffmpeg(name, out)

    log(f"SFX generated: {list(result.keys())}")
    return result


def plan_sfx_placement(
    words: list[dict],
    transition_times: list[float],
    script: str,
) -> list[dict]:
    """Plan where to place SFX based on word timestamps and transitions.

    Returns list of {"type": str, "time": float, "volume": float}.
    """
    placements = []

    # Whoosh 10ms before each transition
    for t in transition_times:
        placements.append({"type": "whoosh", "time": max(0, t - 0.01), "volume": 0.5})

    # Bass drop at hook (first 2 seconds — on the first CAPS word)
    bass_placed = False
    for w in (words or [])[:20]:
        if w.get("word", "").isupper() and len(w.get("word", "")) > 2:
            placements.append({"type": "bass_drop", "time": w["start"], "volume": 0.6})
            bass_placed = True
            break

    # Impact on CAPS words throughout
    for w in (words or []):
        if w.get("word", "").isupper() and len(w.get("word", "")) > 2:
            placements.append({"type": "impact", "time": w["start"], "volume": 0.35})

    # Deduplicate — no two SFX within 0.5s
    placements.sort(key=lambda p: p["time"])
    filtered = []
    last_time = -1.0
    for p in placements:
        if p["time"] - last_time >= 0.5:
            filtered.append(p)
            last_time = p["time"]

    return filtered


def mix_sfx_track(sfx_placements: list[dict], sfx_set: dict[str, Path],
                  duration: float, output_path: Path) -> Path | None:
    """Pre-mix all SFX into a single audio track at planned timestamps."""
    if not sfx_placements:
        return None
    # Create silence base
    run_cmd([
        "ffmpeg", "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo",
        "-t", str(duration), str(output_path), "-y", "-loglevel", "quiet",
    ])
    # Overlay each SFX
    current = output_path
    for i, p in enumerate(sfx_placements):
        sfx_file = sfx_set.get(p["type"])
        if not sfx_file or not sfx_file.exists():
            continue
        next_out = output_path.with_name(f"sfx_mix_{i}.mp3")
        delay_ms = int(p["time"] * 1000)
        run_cmd([
            "ffmpeg", "-i", str(current), "-i", str(sfx_file),
            "-filter_complex",
            f"[1:a]adelay={delay_ms}|{delay_ms},volume={p['volume']}[s];[0:a][s]amix=inputs=2:duration=first[out]",
            "-map", "[out]", str(next_out), "-y", "-loglevel", "quiet",
        ])
        current = next_out
    # Rename final to output
    if current != output_path:
        current.rename(output_path)
    return output_path
