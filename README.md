# YouTube Shorts Pipeline v2

> Turn a one-line topic into a published YouTube Short in minutes.
> Fully automated: **research -> script -> AI visuals -> voiceover -> captions -> music -> upload.**

---

## What's New in v2

- **Burned-in captions** — word-by-word highlight via ASS subtitles (Whisper word timestamps)
- **Background music** — bundled royalty-free tracks with automatic voice-ducking
- **Topic engine** — discover trending topics from Reddit, RSS, Google Trends, Twitter, TikTok
- **Thumbnail generation** — Gemini Imagen + Pillow text overlay, auto-uploaded
- **Resume capability** — pipeline state tracked per stage, re-runs skip completed work
- **Retry logic** — exponential backoff on all API calls (Gemini, ElevenLabs, Claude, YouTube)
- **Structured logging** — file + console logging, `--verbose` for debug output
- **78 tests** — comprehensive test suite across all modules

---

## Pipeline Stages

| Stage | What happens |
|-------|-------------|
| **Draft** | DuckDuckGo research -> Claude script -> b-roll prompts, YouTube metadata, thumbnail prompt |
| **Produce** | Gemini Imagen b-roll (Ken Burns) -> ElevenLabs voiceover -> Whisper captions (ASS + SRT) -> music selection + ducking -> ffmpeg assembly with burned-in captions + background music |
| **Upload** | YouTube upload with metadata + SRT captions + AI thumbnail |

**Anti-hallucination gate:** Claude only uses names/facts from live DuckDuckGo research.

---

## Quick Start

**1. Install dependencies**
```bash
pip install anthropic google-api-python-client google-auth google-auth-oauthlib \
            pillow requests openai-whisper feedparser
```

**2. Run the pipeline (setup wizard launches on first run)**
```bash
cd youtube-shorts-pipeline
python -m pipeline run --news "your topic here" --dry-run
```

**3. Set up YouTube OAuth (when ready to upload)**
```bash
python scripts/setup_youtube_oauth.py
```

---

## Usage

### Draft — generate script and metadata
```bash
python -m pipeline draft --news "your topic"
python -m pipeline draft --discover              # use topic engine
python -m pipeline draft --discover --auto-pick   # let Claude pick
```

### Produce — generate video from a saved draft
```bash
python -m pipeline produce --draft ~/.youtube-shorts-pipeline/drafts/<id>.json
python -m pipeline produce --draft <path> --force  # redo all stages
```

### Upload — push to YouTube with thumbnail
```bash
python -m pipeline upload --draft ~/.youtube-shorts-pipeline/drafts/<id>.json
```

### Full pipeline
```bash
python -m pipeline run --news "your topic"
python -m pipeline run --discover --auto-pick     # trending topic, auto-selected
```

### Discover trending topics
```bash
python -m pipeline topics
python -m pipeline topics --limit 20
```

### Options
- `--lang en|hi` — language for voiceover + captions
- `--verbose` — debug logging
- `--force` — redo completed stages
- `--dry-run` — draft only, skip produce/upload
- `--context "..."` — channel context for script generation

---

## Topic Sources

| Source | Method | Auth |
|--------|--------|------|
| Reddit | `.json` API (hot/trending) | None |
| RSS | `feedparser` (any feed URL) | None |
| Google Trends | `pytrends` library | None |
| Twitter/X | Public trends API | Optional |
| TikTok | Apify actor | Optional |

Configure in `~/.youtube-shorts-pipeline/config.json`:
```json
{
  "topic_sources": {
    "reddit": {"enabled": true, "subreddits": ["technology", "worldnews"]},
    "rss": {"enabled": true, "feeds": ["https://hnrss.org/frontpage"]},
    "google_trends": {"enabled": true, "geo": "IN"}
  }
}
```

---

## Configuration

Keys in `~/.youtube-shorts-pipeline/config.json` (0600 permissions):

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `GEMINI_API_KEY` | Yes | Gemini Imagen API key |
| `ELEVENLABS_API_KEY` | Optional | ElevenLabs TTS (fallback: macOS `say`) |
| `VOICE_ID_EN` | Optional | ElevenLabs voice ID for English |
| `VOICE_ID_HI` | Optional | ElevenLabs voice ID for Hindi |

Environment variables take priority over the config file.

---

## Project Structure

```
youtube-shorts-pipeline/
├── pyproject.toml
├── music/                     # Bundled royalty-free tracks
├── pipeline/
│   ├── __main__.py            # CLI entry point
│   ├── config.py              # Keys, paths, constants, setup wizard
│   ├── state.py               # Resume capability (stage tracking)
│   ├── retry.py               # @with_retry exponential backoff
│   ├── log.py                 # Structured file + console logging
│   ├── research.py            # DuckDuckGo research
│   ├── draft.py               # Claude script generation
│   ├── broll.py               # Gemini Imagen + Ken Burns
│   ├── voiceover.py           # ElevenLabs TTS + macOS say
│   ├── captions.py            # Whisper word timestamps + ASS/SRT
│   ├── music.py               # Track selection + ducking
│   ├── assemble.py            # ffmpeg video assembly
│   ├── thumbnail.py           # Gemini thumbnail + Pillow overlay
│   ├── upload.py              # YouTube API upload
│   └── topics/                # Multi-source topic engine
│       ├── base.py, engine.py
│       ├── reddit.py, rss.py
│       ├── google_trends.py
│       ├── twitter.py, tiktok.py
│       └── manual.py
├── tests/                     # 78 tests
├── scripts/
│   └── setup_youtube_oauth.py
└── references/
    ├── setup.md
    └── troubleshooting.md
```

---

## Cost per Video

| Service | Cost |
|---------|------|
| Anthropic (Claude Sonnet) | ~$0.02 |
| Google Gemini Imagen (3 b-roll + 1 thumbnail) | ~$0.04 |
| ElevenLabs (60-90 sec) | ~$0.05 |
| **Total** | **~$0.11** |

---

## Testing

```bash
pip install pytest pytest-mock
python -m pytest tests/ -v
```

---

## Troubleshooting

See [`references/troubleshooting.md`](references/troubleshooting.md).

---

## Licence

MIT
