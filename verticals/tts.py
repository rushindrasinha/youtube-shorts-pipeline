from __future__ import annotations
"""Multi-provider TTS — Edge TTS (free default), ElevenLabs (premium), macOS say (fallback).

Edge TTS is the recommended default: free, cross-platform, 300+ voices, no API key.
ElevenLabs is premium: most natural, requires API key.
macOS say is the last-resort fallback.
"""

import os
from pathlib import Path

import requests

from .async_helpers import run_async
from .config import VOICE_ID_EN, VOICE_ID_HI, get_elevenlabs_key, run_cmd
from .fallback import FallbackChain
from .log import log
from .retry import with_retry


# ─────────────────────────────────────────────────────
# Edge TTS — free, cross-platform, 300+ voices
# ─────────────────────────────────────────────────────

# Default Edge TTS voices per language
EDGE_VOICES = {
    "en": "en-US-AndrewMultilingualNeural",
    "hi": "hi-IN-MadhurNeural",
    "es": "es-MX-JorgeNeural",
    "pt": "pt-BR-AntonioNeural",
    "de": "de-DE-ConradNeural",
    "fr": "fr-FR-HenriNeural",
    "ja": "ja-JP-KeitaNeural",
    "ko": "ko-KR-InJoonNeural",
}


async def _edge_tts_generate(text: str, voice: str, output_path: Path):
    """Generate audio via edge-tts (async)."""
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))


def _generate_edge_tts(script: str, out_dir: Path, lang: str, voice_override: str = "") -> Path:
    """Generate voiceover via Edge TTS (free Microsoft voices)."""
    voice = voice_override or EDGE_VOICES.get(lang[:2], EDGE_VOICES["en"])
    out_path = out_dir / f"voiceover_{lang}.mp3"

    log(f"Generating {lang} voiceover via Edge TTS (voice: {voice})...")

    try:
        run_async(_edge_tts_generate(script, voice, out_path), timeout=60)
        log(f"Edge TTS voiceover saved: {out_path.name}")
        return out_path
    except Exception as e:
        raise RuntimeError(f"Edge TTS failed: {e}")


# ─────────────────────────────────────────────────────
# Kokoro TTS — free, local, #1 on HuggingFace TTS Arena (Jan 2026)
# 82M params, runs on CPU, Apache 2.0 license
# Install: pip install "kokoro==0.7.16" soundfile && brew install espeak-ng
# ─────────────────────────────────────────────────────

KOKORO_VOICES = {
    "en": "am_adam",       # measured male, great for science narration
    "en_female": "bf_emma", # British female, clean and authoritative
}


def _generate_kokoro(script: str, out_dir: Path, lang: str, voice_override: str = "") -> Path:
    """Generate voiceover via Kokoro TTS (free, local, high quality)."""
    try:
        from kokoro import KPipeline
        import soundfile as sf
        import numpy as np
    except ImportError:
        raise RuntimeError(
            "Kokoro not installed. Run:\n"
            "  pip install 'kokoro==0.7.16' soundfile\n"
            "  brew install espeak-ng"
        )

    voice = voice_override or KOKORO_VOICES.get(lang[:2], KOKORO_VOICES["en"])
    out_path = out_dir / f"voiceover_{lang}.wav"
    mp3_path = out_dir / f"voiceover_{lang}.mp3"

    log(f"Generating {lang} voiceover via Kokoro TTS (voice: {voice})...")

    lang_code = "a" if lang.startswith("en") else lang[:2]
    pipeline = KPipeline(lang_code=lang_code)

    audio_chunks = []
    for _, _, audio in pipeline(script, voice=voice, speed=0.95):
        audio_chunks.append(audio)

    audio_data = np.concatenate(audio_chunks)
    sf.write(str(out_path), audio_data, 24000)

    # Convert wav → mp3
    run_cmd([
        "ffmpeg", "-i", str(out_path), "-acodec", "libmp3lame", "-q:a", "2",
        str(mp3_path), "-y", "-loglevel", "quiet",
    ])
    out_path.unlink(missing_ok=True)

    log(f"Kokoro voiceover saved: {mp3_path.name}")
    return mp3_path


# ─────────────────────────────────────────────────────
# ElevenLabs — premium, most natural
# ─────────────────────────────────────────────────────

@with_retry(max_retries=3, base_delay=2.0)
def _call_elevenlabs(script: str, voice_id: str, api_key: str, settings: dict | None = None) -> bytes:
    """Call ElevenLabs TTS API and return audio bytes."""
    voice_settings = settings or {
        "stability": 0.4,
        "similarity_boost": 0.85,
        "style": 0.3,
        "use_speaker_boost": True,
    }
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "text": script,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": voice_settings,
        },
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:200]}")
    return r.content


def _generate_elevenlabs(
    script: str, out_dir: Path, lang: str,
    voice_id: str = "", settings: dict | None = None
) -> Path:
    """Generate voiceover via ElevenLabs."""
    api_key = get_elevenlabs_key()
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY not set")

    vid = voice_id or (VOICE_ID_HI if lang == "hi" else VOICE_ID_EN)
    out_path = out_dir / f"voiceover_{lang}.mp3"

    log(f"Generating {lang} voiceover via ElevenLabs (voice: {vid})...")
    audio_bytes = _call_elevenlabs(script, vid, api_key, settings)
    out_path.write_bytes(audio_bytes)
    log(f"ElevenLabs voiceover saved: {out_path.name}")
    return out_path


# ─────────────────────────────────────────────────────
# macOS say — last resort fallback
# ─────────────────────────────────────────────────────

def _generate_say(script: str, out_dir: Path) -> Path:
    """macOS 'say' fallback TTS."""
    out_path = out_dir / "voiceover_say.aiff"
    mp3_path = out_dir / "voiceover_say.mp3"
    run_cmd(["say", "-o", str(out_path), script])
    run_cmd([
        "ffmpeg", "-i", str(out_path), "-acodec", "libmp3lame",
        str(mp3_path), "-y", "-loglevel", "quiet",
    ])
    return mp3_path


# ─────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────

def get_tts_provider(name: str | None = None) -> str:
    """Resolve which TTS provider to use.

    Priority: explicit name > TTS_PROVIDER env > auto-detect.
    Auto-detect tries: edge_tts > elevenlabs > say.
    """
    if name and name != "auto":
        return name.lower()

    from_env = os.environ.get("TTS_PROVIDER", "").lower()
    if from_env:
        return from_env

    from .config import load_config
    from_cfg = load_config().get("TTS_PROVIDER", "").lower()
    if from_cfg:
        return from_cfg

    # Auto-detect: Kokoro first (best free quality), then Edge TTS, then ElevenLabs
    try:
        import kokoro  # noqa: F401
        return "kokoro"
    except ImportError:
        pass

    try:
        import edge_tts  # noqa: F401
        return "edge"
    except ImportError:
        pass

    if get_elevenlabs_key():
        return "elevenlabs"

    # macOS say as last resort
    import shutil
    if shutil.which("say"):
        return "say"

    raise RuntimeError(
        "No TTS provider available. Install one:\n"
        "  pip install edge-tts  (free, recommended)\n"
        "  Set ELEVENLABS_API_KEY (premium)\n"
        "  Or use macOS (has built-in 'say')"
    )


def generate_voiceover(
    script: str,
    out_dir: Path,
    lang: str = "en",
    provider: str | None = None,
    voice_config: dict | None = None,
) -> Path:
    """Generate voiceover via the configured TTS provider.

    Args:
        script: The voiceover text.
        out_dir: Directory to save the audio file.
        lang: Language code (en, hi, es, etc.).
        provider: TTS provider name (edge, elevenlabs, say).
        voice_config: Optional voice config from niche profile.

    Returns:
        Path to the generated audio file.
    """
    provider = get_tts_provider(provider)
    voice_config = voice_config or {}
    voice_override = voice_config.get("voice_id", "")

    # Build a fallback chain rooted at the resolved provider.
    # Providers earlier in the preference order than the resolved one are skipped.
    order = ["kokoro", "edge", "elevenlabs", "say"]
    start = order.index(provider) if provider in order else 0

    chain = FallbackChain("tts")
    if start <= order.index("kokoro"):
        chain.add("kokoro", lambda: _generate_kokoro(script, out_dir, lang, voice_override))
    if start <= order.index("edge"):
        chain.add("edge", lambda: _generate_edge_tts(script, out_dir, lang, voice_override))
    if start <= order.index("elevenlabs"):
        chain.add(
            "elevenlabs",
            lambda: _generate_elevenlabs(
                script, out_dir, lang,
                voice_id=voice_config.get("voice_id", ""),
                settings=voice_config.get("settings"),
            ),
            condition=get_elevenlabs_key,
        )
    chain.add("say", lambda: _generate_say(script, out_dir))

    return chain.execute()
