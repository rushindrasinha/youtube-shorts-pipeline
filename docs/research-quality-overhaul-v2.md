# Research Report: Making YouTube Shorts Not Look AI-Generated
**Date:** 2026-04-02
**Method:** 7 parallel deep research agents with web search
**Status:** Ready for implementation

## Executive Summary

Our pipeline produces what the internet calls "the AI slop formula" — a pattern so recognizable that viewers identify it in under 2 seconds. The research identifies 5 critical problems and specific fixes.

## The 5 Critical Problems (Ordered by Detection Speed)

### 1. Still Images With Ken Burns = Instant AI Detection
- Zero parallax — foreground/background move at same rate
- Fix: DepthFlow 2.5D parallax (`pip install depthflow`) + Pexels stock video mixed in
- Target: 40-60% real stock footage, DepthFlow on AI images

### 2. Voice Is Too Slow and Monotone
- Target: 170-180 WPM (we're at ~130)
- Add `speed: 1.08` to ElevenLabs API call (missing entirely)
- Target 150-165 words per script (currently 120-140)
- Use v3 audio tags: `[excited]` hook → `[conversational tone]` body → `[dramatic tone]` reveal
- Add imperfection: `[sighs]`, `[laughs]`, `[hesitates]` — one per script

### 3. Visual Changes Every 2-3 Seconds, Not 10
- Need 18-22 visual moments in 50 seconds, not 5
- Mix 3-5 source types: AI images + stock footage + kinetic text + data viz
- Text overlays on 60-80% of segments
- Pattern interrupts every 8-12 seconds

### 4. Zero Sound Design
- Professional shorts: 10-20 SFX per minute. We have zero.
- Whooshes 10ms before transitions, impacts on CAPS words, bass drop at hook
- Use ElevenLabs Sound Effects API or pre-bundled library from Mixkit/Freesound
- Place using ffmpeg `adelay` + `amix` at Whisper word timestamps

### 5. The "AI Slop Formula" Is Our Exact Pipeline
- Uniform frame durations → vary them
- Always 5 frames → vary between 8-20
- Wall-to-wall narration → add silence/breathing room
- Predictable pacing → emotional arc (slow hook → fast body → slower reveal)

## Top 10 Implementation Actions (Priority Order)

1. **Pexels Video API** — mix real stock footage with AI images (free, low effort)
2. **ElevenLabs `speed: 1.08`** — one line, instant voice improvement
3. **v3 audio tags in script prompt** — `[excited]`, `[pause]`, `[dramatic tone]`
4. **SFX layer** — whooshes, impacts, bass drops (ElevenLabs SFX API or Freesound)
5. **DepthFlow parallax** — replace Ken Burns with 2.5D depth motion (`pip install depthflow`)
6. **Color grading LUTs** — 3-5 .cube files via ffmpeg `lut3d` (free)
7. **Vary frame durations** — stop equal division, weight by content importance
8. **Increase script words to 150-165** — hits 170-180 WPM
9. **Text overlays via Remotion** — animated stats, emphasis words, lists
10. **Pre-bundle SFX library** — 5-8 whooshes, 3-4 impacts, 2 risers from Mixkit

## Tool Integration Reference

| Tool | Purpose | Cost | Install |
|------|---------|------|---------|
| Pexels Video API | Real stock b-roll | Free (200 req/hr) | `pip install pexels-api-py` |
| DepthFlow | 2.5D parallax from stills | Free (GPU req) | `pip install depthflow` |
| ElevenLabs SFX API | Sound effects generation | Uses existing key | Already integrated |
| Freesound API | SFX library search | Free (OAuth2) | `pip install freesound-python` |
| Real-ESRGAN | Image upscaling | Free (GPU) | `pip install realesrgan` |
| Kling 3.0 | Image-to-video | ~$0.14/clip | REST API |
| Color LUTs | Film-look grading | Free | Download .cube files |

## Voice Settings Reference

| Parameter | Current | Recommended |
|-----------|---------|-------------|
| model_id | eleven_v3 | eleven_v3 (correct) |
| stability | 0.30 | 0.30-0.35 |
| similarity_boost | 0.70 | 0.70-0.75 |
| style | 0.45 | 0.35-0.50 |
| speed | 1.0 (default) | **1.05-1.10** (MISSING) |
| Script words | 120-140 | **150-165** |

## SFX Placement Rules

| Event | SFX Type | Timing |
|-------|----------|--------|
| Scene transition | Whoosh | 10ms BEFORE cut |
| Hook word (0-3s) | Bass drop + impact | On stressed syllable |
| CAPS word | Subtle pop | On word start |
| Text appearance | Ping | At frame text appears |
| Before reveal | Riser | 1.5-3s before |

## Post-Implementation Assessment (2026-04-02)

Items 2-10 were implemented and shipped. Produced a Bitcoin test video with the full stack.

**Key finding: Problem #1 is the whole ballgame.** Still images — even with stock footage mixed in, color grading, variable timing, SFX, and emotional voice — don't pass the eye test. The output needs to be actual video with real motion, not animated stills with Ken Burns.

**Revised path forward:** Replace Ken Burns / DepthFlow with image-to-video AI models (Kling, Runway, Minimax, etc.) that generate 5-10 second video clips from our AI frames. The pipeline architecture already supports this — the `animate_frame()` function in `broll.py` is the swap point. Everything else we built (voice, SFX, grading, timing) will land much harder once the visual foundation is actual video.

## Sources
- Kapwing AI Slop Study, Faux Lens Journal, NPR, ElevenLabs docs
- MrBeast editor interviews, OpusClip retention data
- DepthFlow GitHub, Pexels API, Freesound API
- 50+ sources cited in full agent reports
