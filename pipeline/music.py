"""Background music — ElevenLabs AI generation + local fallback + volume ducking."""

import random
from pathlib import Path

import requests

from .config import get_elevenlabs_key
from .log import log
from .retry import with_retry

# Local music directory as fallback
MUSIC_DIR = Path(__file__).resolve().parent.parent / "music"


@with_retry(max_retries=2, base_delay=3.0)
def _generate_music_elevenlabs(prompt: str, duration_ms: int, api_key: str) -> bytes:
    """Generate background music via ElevenLabs Music API."""
    r = requests.post(
        "https://api.elevenlabs.io/v1/music",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "prompt": prompt,
            "music_length_ms": duration_ms,
        },
        timeout=120,
    )
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs Music {r.status_code}: {r.text[:200]}")
    return r.content


def _find_tracks() -> list[Path]:
    """Find all MP3 tracks in the music/ directory."""
    if not MUSIC_DIR.exists():
        return []
    return sorted(MUSIC_DIR.glob("*.mp3"))


def _words_to_speech_regions(words: list[dict]) -> list[tuple[float, float]]:
    """Merge word timestamps into speech regions (gap < 0.5s = same region)."""
    if not words:
        return []
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


def _get_speech_regions(audio_path: Path, words: list[dict] | None = None) -> list[tuple[float, float]]:
    """Extract speech regions from word timestamps.

    If `words` are provided (from captions stage), uses them directly to avoid
    running Whisper twice. Otherwise falls back to Whisper or whole-audio region.
    """
    if words:
        return _words_to_speech_regions(words)

    try:
        from .captions import _whisper_word_timestamps
        w = _whisper_word_timestamps(audio_path)
        if w:
            return _words_to_speech_regions(w)
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


# Genre-specific music prompts for professional-quality background tracks
_MUSIC_PROMPTS = {
    "tech": (
        "Minimal electronic ambient, 85 BPM, C minor. "
        "Soft synth pads with subtle vinyl crackle and tape hiss. "
        "Muted kick drum every 4 beats. Warm analog feel. "
        "Instrumental only, no vocals, no melody."
    ),
    "story": (
        "Acoustic lo-fi, 70 BPM, G major. "
        "Gentle fingerpicked nylon guitar with soft brush drums. "
        "Warm room reverb, slight tape saturation. "
        "Instrumental only, no vocals."
    ),
    "hype": (
        "Upbeat trap-influenced lo-fi, 95 BPM, A minor. "
        "808 sub bass, crispy hi-hats, filtered piano chords. "
        "Energetic but not overwhelming. "
        "Instrumental only, no vocals."
    ),
    "dark": (
        "Dark ambient drone, 60 BPM, D minor. "
        "Deep sub bass with distant reverb tails. "
        "Sparse piano notes with heavy reverb. Mysterious tension. "
        "Instrumental only, no vocals."
    ),
    "uplifting": (
        "Uplifting cinematic instrumental, 110 BPM, C major. "
        "Piano arpeggios, orchestral strings building, hopeful brass. "
        "Warm and inspiring. "
        "Instrumental only, no vocals."
    ),
    "default": (
        "Chill lo-fi hip-hop instrumental, 80 BPM, E minor. "
        "Rhodes electric piano with vinyl noise and tape wobble. "
        "Soft boom-bap drums, subtle bass. Coffee shop warmth. "
        "Instrumental only, no vocals."
    ),
}

# Keyword-to-mood mapping
_MOOD_KEYWORDS = {
    "tech": ["ai", "gpt", "openai", "tech", "software", "code", "robot", "nvidia", "chip", "crypto", "bitcoin", "hack"],
    "story": ["story", "history", "ancient", "journey", "life", "memoir", "biography"],
    "hype": ["viral", "amazing", "incredible", "insane", "record", "fastest", "biggest", "win", "champion"],
    "dark": ["dark", "crime", "mystery", "conspiracy", "secret", "terror", "war", "threat", "danger"],
    "uplifting": ["inspire", "hope", "achieve", "success", "dream", "hero", "discover", "breakthrough", "moon", "mars", "space", "nasa"],
}


def _classify_mood(topic: str) -> str:
    """Classify topic into a mood category for music selection."""
    topic_lower = topic.lower()
    scores = {}
    for mood, keywords in _MOOD_KEYWORDS.items():
        scores[mood] = sum(1 for kw in keywords if kw in topic_lower)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "default"


def _build_music_prompt(topic: str) -> str:
    """Build a genre-specific music prompt based on topic mood."""
    mood = _classify_mood(topic)
    base = _MUSIC_PROMPTS.get(mood, _MUSIC_PROMPTS["default"])
    if topic:
        return f"{base} Background for a YouTube Short about: {topic[:80]}."
    return base


def select_and_prepare_music(
    voiceover_path: Path,
    work_dir: Path,
    words: list[dict] | None = None,
    topic: str = "",
) -> dict:
    """Generate or select background music, build duck filter from speech regions.

    Tries ElevenLabs Music API first (AI-generated music matching the topic),
    then falls back to local tracks in the music/ directory.

    Returns dict with track_path and duck_filter for use by assemble.py.
    """
    api_key = get_elevenlabs_key()
    track_path = None

    # Try ElevenLabs AI music generation with genre-specific prompts
    if api_key:
        try:
            from .assemble import get_audio_duration
            duration = get_audio_duration(voiceover_path)
            duration_ms = int(min(duration + 2, 59) * 1000)

            prompt = _build_music_prompt(topic)
            log(f"Generating background music via ElevenLabs ({_classify_mood(topic)} mood)...")
            audio_bytes = _generate_music_elevenlabs(prompt, duration_ms, api_key)
            track_path = work_dir / "music_ai.mp3"
            track_path.write_bytes(audio_bytes)
            log(f"AI music generated: {track_path.name} ({len(audio_bytes) // 1024}KB)")
        except Exception as e:
            log(f"ElevenLabs Music failed: {e} — trying local tracks")

    # Fallback: local tracks
    if not track_path:
        tracks = _find_tracks()
        if not tracks:
            log("No music tracks available — skipping background music")
            return {}
        track_path = random.choice(tracks)
        log(f"Selected local music track: {track_path.name}")

    # Get speech regions for ducking (reuse words from captions if available)
    speech_regions = _get_speech_regions(voiceover_path, words=words)
    duck_filter = build_duck_filter(speech_regions)
    log(f"Built duck filter with {len(speech_regions)} speech regions")

    return {
        "track_path": str(track_path),
        "duck_filter": duck_filter,
    }
