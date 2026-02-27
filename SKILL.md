---
name: youtube-shorts-pipeline
description: "Fully automated YouTube Shorts production pipeline v2. Takes a one-line news item or topic and outputs a finished, uploaded YouTube Short — with AI-generated b-roll (Gemini Imagen), professional voiceover (ElevenLabs), burned-in word-by-word captions (Whisper + ASS), background music with voice-ducking, AI thumbnail, and direct YouTube upload. Includes multi-source trending topic discovery (Reddit, RSS, Google Trends), resume capability, retry logic, and structured logging. Use when asked to create a YouTube Short, produce a news short, discover trending topics, or run the content pipeline."
---

# YouTube Shorts Pipeline v2

Fully automated: news headline -> research -> script -> AI visuals -> voiceover -> captions -> music -> thumbnail -> upload.

> **First run triggers an automatic setup wizard** — just run any command.

## What it does

1. **Draft** — Researches topic via DuckDuckGo, Claude writes script, generates b-roll/thumbnail prompts + YouTube metadata
2. **Produce** — Gemini Imagen b-roll (Ken Burns) + ElevenLabs voiceover + Whisper word-level captions (ASS burn-in) + background music (auto-ducking) + ffmpeg assembly
3. **Upload** — YouTube upload with metadata + SRT captions + AI thumbnail

## Setup (one-time)

On first run, the pipeline prompts for:
- `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `ELEVENLABS_API_KEY` (optional)

Config: `~/.youtube-shorts-pipeline/config.json`

Required:
```bash
brew install ffmpeg
pip install anthropic google-api-python-client google-auth google-auth-oauthlib \
            pillow requests openai-whisper feedparser
```

## Commands

### Draft
```bash
python -m pipeline draft --news "headline"
python -m pipeline draft --discover              # trending topics
python -m pipeline draft --discover --auto-pick   # Claude picks
```

### Produce
```bash
python -m pipeline produce --draft ~/.youtube-shorts-pipeline/drafts/<id>.json [--lang en|hi] [--force]
```

### Upload
```bash
python -m pipeline upload --draft <path> [--lang en|hi]
```

### Full auto
```bash
python -m pipeline run --news "headline" [--dry-run]
python -m pipeline run --discover --auto-pick
```

### Discover trending topics
```bash
python -m pipeline topics [--limit 20]
```

## Features

- **Burned-in captions**: Word-by-word yellow highlight via ASS subtitles (Whisper word timestamps)
- **Background music**: Bundled royalty-free tracks, auto-ducking during speech
- **Topic engine**: Reddit, RSS, Google Trends, Twitter, TikTok sources with parallel fetch
- **Thumbnails**: Gemini Imagen (16:9) + Pillow title overlay
- **Resume**: Re-runs skip completed stages; `--force` to redo
- **Retry**: Exponential backoff on all API calls
- **Logging**: `~/.youtube-shorts-pipeline/logs/`, `--verbose` for debug

## Key Rules

- **Anti-hallucination**: Claude ONLY uses names/facts from live DuckDuckGo research
- **Hindi**: Native Hinglish writing, never translation
- **YouTube quota**: `uploadLimitExceeded` = daily cap hit, wait 24h

## Topic Source Config

```json
{
  "topic_sources": {
    "reddit": {"enabled": true, "subreddits": ["technology", "worldnews"]},
    "rss": {"enabled": true, "feeds": ["https://hnrss.org/frontpage"]},
    "google_trends": {"enabled": true, "geo": "IN"}
  }
}
```

## File locations

- Config: `~/.youtube-shorts-pipeline/config.json`
- Drafts: `~/.youtube-shorts-pipeline/drafts/<timestamp>.json`
- Videos: `~/.youtube-shorts-pipeline/media/pipeline_<id>_<lang>.mp4`
- Logs: `~/.youtube-shorts-pipeline/logs/pipeline_YYYYMMDD.log`

## Troubleshooting

See `references/troubleshooting.md`.
