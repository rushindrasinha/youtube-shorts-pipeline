"""Background music — track selection + volume ducking."""

import random
from pathlib import Path

from .log import log

# Music directory ships with the package
MUSIC_DIR = Path(__file__).resolve().parent.parent / "music"


def _find_tracks() -> list[Path]:
    """Find all MP3 tracks in the music/ directory."""
    if not MUSIC_DIR.exists():
        return []
    return sorted(MUSIC_DIR.glob("*.mp3"))


def _get_speech_regions(audio_path: Path) -> list[tuple[float, float]]:
    """Extract speech regions from Whisper word timestamps (reuses captions data).

    Falls back to treating the entire audio as one speech region.
    """
    try:
        from .captions import _whisper_word_timestamps
        words = _whisper_word_timestamps(audio_path)
        if words:
            # Merge close words into speech regions (gap < 0.5s = same region)
            regions = []
            region_start = words[0]["start"]
            region_end = words[0]["end"]

            for w in words[1:]:
                if w["start"] - region_end < 0.5:
                    region_end = w["end"]
                else:
                    regions.append((region_start, region_end))
                    region_start = w["start"]
                    region_end = w["end"]
            regions.append((region_start, region_end))
            return regions
    except Exception:
        pass

    # Fallback: get total duration and treat as one speech region
    try:
        from .assemble import get_audio_duration
        dur = get_audio_duration(audio_path)
        return [(0.0, dur)]
    except Exception:
        return [(0.0, 60.0)]


def build_duck_filter(speech_regions: list[tuple[float, float]], buffer: float = 0.3) -> str:
    """Build ffmpeg volume filter expression for ducking during speech.

    During speech: volume = 0.12
    During gaps: volume = 0.25
    Transitions smoothed by ±buffer seconds.
    """
    if not speech_regions:
        return "volume=0.25"

    # Build between() conditions for speech regions
    conditions = []
    for start, end in speech_regions:
        # Add buffer for smooth transition
        s = max(0, start - buffer)
        e = end + buffer
        conditions.append(f"between(t,{s:.2f},{e:.2f})")

    condition_expr = "+".join(conditions)
    return f"volume='if({condition_expr}, 0.12, 0.25)':eval=frame"


def select_and_prepare_music(voiceover_path: Path, work_dir: Path) -> dict:
    """Select a random track, build duck filter from speech regions.

    Returns dict with track_path and duck_filter for use by assemble.py.
    """
    tracks = _find_tracks()
    if not tracks:
        log("No music tracks found in music/ — skipping background music")
        return {}

    track = random.choice(tracks)
    log(f"Selected music track: {track.name}")

    # Get speech regions for ducking
    speech_regions = _get_speech_regions(voiceover_path)
    duck_filter = build_duck_filter(speech_regions)
    log(f"Built duck filter with {len(speech_regions)} speech regions")

    return {
        "track_path": str(track),
        "duck_filter": duck_filter,
    }
