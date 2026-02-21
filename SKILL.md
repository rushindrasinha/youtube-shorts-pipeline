---
name: youtube-shorts-pipeline
description: "Fully automated YouTube Shorts production pipeline. Takes a one-line news item or topic and outputs a finished, uploaded YouTube Short — complete with AI-generated b-roll visuals (Gemini Imagen), professional voiceover (ElevenLabs), SRT captions in English and Hindi, and direct YouTube upload via OAuth. Anti-hallucination research gate built in. Use when asked to create a YouTube Short, produce a news short, automate video content, run the content pipeline, draft/produce/upload a short-form video, or generate a faceless YouTube channel video."
---

# YouTube Shorts Pipeline

Fully automated pipeline: news headline → research → script → AI visuals → voiceover → captions → upload.

> **First run triggers an automatic setup wizard** — just run any command and you'll be guided through API key configuration and YouTube OAuth.

## What it does

1. **Draft** — Researches topic via DuckDuckGo, writes Claude script, generates Gemini image prompts, YouTube description, Instagram caption, thumbnail prompt
2. **Produce** — Gemini Imagen generates 3 b-roll frames (Ken Burns animation), ElevenLabs synthesises voiceover, ffmpeg assembles final video with captions
3. **Upload** — Pushes to YouTube with title, description, tags, and SRT caption tracks (EN + HI)

## Setup (one-time)

See `references/setup.md` for full instructions.

On **first run**, the pipeline automatically prompts for:
- `ANTHROPIC_API_KEY` — Claude script generation
- `ELEVENLABS_API_KEY` — voiceover (optional; macOS `say` fallback available)
- `GEMINI_API_KEY` — AI b-roll image generation

Config saved to: `~/.youtube-shorts-pipeline/config.json`

Required binaries:
```bash
# macOS
brew install ffmpeg
pip install openai-whisper

# Linux
apt install ffmpeg
pip install openai-whisper
```

Required Python packages:
```bash
pip install anthropic google-api-python-client google-auth google-auth-oauthlib \
            pillow requests
```

## Commands

> Replace `{skillDir}` with the path where you extracted this skill.

### Draft only
```bash
python3 {skillDir}/scripts/pipeline.py draft --news "your news headline here"
```

### Produce from draft
```bash
python3 {skillDir}/scripts/pipeline.py produce --draft ~/.youtube-shorts-pipeline/drafts/<id>.json --lang en
python3 {skillDir}/scripts/pipeline.py produce --draft ~/.youtube-shorts-pipeline/drafts/<id>.json --lang hi
```

### Upload
```bash
python3 {skillDir}/scripts/pipeline.py upload --draft ~/.youtube-shorts-pipeline/drafts/<id>.json --lang en
python3 {skillDir}/scripts/pipeline.py upload --draft ~/.youtube-shorts-pipeline/drafts/<id>.json --lang hi
```

### Full auto (draft → produce → upload)
```bash
python3 {skillDir}/scripts/pipeline.py run --news "your news headline here"
```

### Dry run (draft only, no video/upload)
```bash
python3 {skillDir}/scripts/pipeline.py run --news "your news headline here" --dry-run
```

## Key Rules

- **Anti-hallucination**: Claude ONLY uses names/facts found in live DuckDuckGo research. Never fabricates player names, scores, or events.
- **Hindi**: Always native Hinglish writing, never translation. Fresh script for Hindi-speaking Indian audience.
- **Whisper + Hindi**: Whisper outputs Urdu script for Hindi audio — use Whisper timings + manually write Devanagari SRT.
- **YouTube quota**: `uploadLimitExceeded` = daily cap hit. Wait 24h.

## File locations

- Config: `~/.youtube-shorts-pipeline/config.json`
- Drafts: `~/.youtube-shorts-pipeline/drafts/<timestamp>.json`
- Videos: `~/.youtube-shorts-pipeline/media/pipeline_<id>_<lang>.mp4`
- SRTs: `~/.youtube-shorts-pipeline/media/pipeline_<id>_<lang>.srt`

## Voice IDs (ElevenLabs)

- English VO: `JBFqnCBsd6RMkjVDRZzb` (George — deep, authoritative)
- Override via env: `VOICE_ID_EN=<id>` or `VOICE_ID_HI=<id>`

## Customising

- **Channel topic**: Pass any news item — esports, tech, finance, sports, politics
- **Language**: `--lang en` or `--lang hi` (or extend for any ElevenLabs-supported language)
- **B-roll style**: Edit image prompts in draft JSON before producing
- **Script edits**: Pass `--script "edited script"` to produce command to override Claude's draft

## Troubleshooting

See `references/troubleshooting.md` for common errors and fixes.
