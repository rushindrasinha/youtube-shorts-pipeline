"""ElevenLabs TTS + audio post-processing + macOS say fallback."""

from pathlib import Path

import requests

from .config import VOICE_ID_EN, VOICE_ID_HI, get_elevenlabs_key, run_cmd
from .log import log
from .retry import with_retry

MAX_DURATION = 59.0  # YouTube Shorts limit


@with_retry(max_retries=3, base_delay=2.0)
def _call_elevenlabs(script: str, voice_id: str, api_key: str) -> bytes:
    """Call ElevenLabs TTS API (v3 model for maximum expressiveness)."""
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "text": script,
            "model_id": "eleven_v3",
            "voice_settings": {
                "stability": 0.65,
                "similarity_boost": 0.75,
                "style": 0.0,  # v3 uses inline audio tags for expression
                "use_speaker_boost": True,
            },
        },
        timeout=120,  # v3 is slower but higher quality
    )
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:200]}")
    return r.content


def _post_process_voice(input_path: Path, output_path: Path) -> Path:
    """Professional audio post-processing: EQ, compression, reverb, normalization.

    Chain: highpass → presence boost → warmth → de-ess → compression → limiter → reverb → LUFS
    """
    # Stage 1: EQ + dynamics
    eq_path = output_path.with_name(output_path.stem + "_eq.mp3")
    eq_chain = ",".join([
        "highpass=f=80",                          # remove rumble
        "lowpass=f=14000",                        # remove hiss
        "equalizer=f=3000:t=q:w=1.5:g=3",        # presence boost (+3dB @ 3kHz)
        "equalizer=f=200:t=q:w=1.0:g=1.5",       # warmth (+1.5dB @ 200Hz)
        "equalizer=f=7000:t=q:w=2.0:g=-2",       # de-ess (-2dB @ 7kHz)
        "acompressor=threshold=0.089:ratio=4:attack=5:release=50:makeup=2",
        "alimiter=limit=0.95:attack=5:release=50",
    ])
    try:
        run_cmd([
            "ffmpeg", "-i", str(input_path),
            "-af", eq_chain, "-ar", "48000",
            str(eq_path), "-y", "-loglevel", "quiet",
        ])
    except Exception as e:
        log(f"Audio EQ failed: {e} — skipping post-processing")
        return input_path

    # Stage 2: Subtle room reverb (early reflections via aecho)
    reverb_path = output_path.with_name(output_path.stem + "_reverb.mp3")
    try:
        run_cmd([
            "ffmpeg", "-i", str(eq_path),
            "-af", "aecho=0.8:0.3:15|20:0.15|0.1",
            str(reverb_path), "-y", "-loglevel", "quiet",
        ])
    except Exception:
        reverb_path = eq_path  # skip reverb if it fails

    # Stage 3: Loudness normalize to -14 LUFS (YouTube standard)
    try:
        run_cmd([
            "ffmpeg", "-i", str(reverb_path),
            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
            "-ar", "48000",
            str(output_path), "-y", "-loglevel", "quiet",
        ])
        log("Audio post-processing complete (EQ + reverb + LUFS)")
        return output_path
    except Exception:
        log("LUFS normalization failed — using EQ'd audio")
        return reverb_path


def _say_fallback(script: str, out_dir: Path) -> Path:
    """macOS 'say' fallback TTS."""
    # Strip audio tags that say doesn't understand
    clean = script
    for tag in ["[excited]", "[pause]", "[serious]", "[whispers]", "[dramatic]"]:
        clean = clean.replace(tag, "")
    out_path = out_dir / "voiceover_say.aiff"
    mp3_path = out_dir / "voiceover_say.mp3"
    run_cmd(["say", "-o", str(out_path), "--", clean])
    run_cmd([
        "ffmpeg", "-i", str(out_path), "-acodec", "libmp3lame",
        str(mp3_path), "-y", "-loglevel", "quiet",
    ])
    return mp3_path


def _trim_audio(path: Path, max_dur: float) -> Path:
    """Trim audio to max_dur seconds if it exceeds the limit."""
    from .assemble import get_audio_duration
    dur = get_audio_duration(path)
    if dur <= max_dur:
        return path
    log(f"Voiceover is {dur:.1f}s — trimming to {max_dur:.0f}s")
    trimmed = path.with_name(path.stem + "_trimmed" + path.suffix)
    run_cmd([
        "ffmpeg", "-i", str(path), "-t", str(max_dur),
        "-c", "copy", str(trimmed), "-y", "-loglevel", "quiet",
    ])
    return trimmed


def generate_voiceover(script: str, out_dir: Path, lang: str = "en") -> Path:
    """Generate voiceover via ElevenLabs v3, with post-processing and fallbacks."""
    voice_id = VOICE_ID_HI if lang == "hi" else VOICE_ID_EN
    api_key = get_elevenlabs_key()

    if not api_key:
        log("No ElevenLabs key — using macOS 'say' fallback")
        raw = _say_fallback(script, out_dir)
        processed = _post_process_voice(raw, out_dir / f"voiceover_{lang}.mp3")
        return _trim_audio(processed, MAX_DURATION)

    log(f"Generating {lang} voiceover via ElevenLabs v3...")
    raw_path = out_dir / f"voiceover_{lang}_raw.mp3"

    try:
        audio_bytes = _call_elevenlabs(script, voice_id, api_key)
        raw_path.write_bytes(audio_bytes)
        log(f"Raw voiceover: {raw_path.name}")
    except Exception as e:
        log(f"ElevenLabs failed: {e} — using 'say' fallback")
        raw_path = _say_fallback(script, out_dir)

    # Post-process regardless of source
    processed = _post_process_voice(raw_path, out_dir / f"voiceover_{lang}.mp3")
    return _trim_audio(processed, MAX_DURATION)
