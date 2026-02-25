# YouTube Shorts Pipeline 🎬

> Turn a one-line topic into a published YouTube Short in minutes.  
> Fully automated: **research → script → AI visuals → voiceover → captions → upload.**

---

## What it does

The pipeline has three stages, each runnable independently or as one shot:

| Stage | What happens |
|-------|-------------|
| **Draft** | DuckDuckGo research → Claude writes a 60–90 sec script → Gemini generates b-roll image prompts, YouTube title/description/tags, Instagram caption, thumbnail prompt |
| **Produce** | Gemini Imagen 3 generates 3 AI visuals (9:16 portrait) → Ken Burns animation → ElevenLabs voiceover → ffmpeg assembles video → Whisper generates SRT captions |
| **Upload** | YouTube Data API v3 uploads the video with full metadata + SRT caption track |

**Anti-hallucination gate:** Claude is shown live DuckDuckGo research and instructed to use *only* names, scores, and facts found there. No fabricated content.

---

## Demo

A typical run looks like this:

```
$ python3 scripts/pipeline.py run --news "India wins VCT Pacific 2026"

👋 First run detected. Running setup...
[wizard prompts for API keys...]

🎬 Drafting: India wins VCT Pacific 2026

  Researching topic via DuckDuckGo...
  Found 8 snippets.

✅ Draft saved: ~/.youtube-shorts-pipeline/drafts/1708512345.json

📝 Script:
  "India just made history at VCT Pacific 2026..."

🎬 Producing EN video...
  Generating b-roll frame 1/3 via Gemini Imagen...
  Generating b-roll frame 2/3 via Gemini Imagen...
  Generating b-roll frame 3/3 via Gemini Imagen...
  Generating en voiceover via ElevenLabs...
  Generating SRT captions via Whisper...
  Assembling video...
  Video assembled: ~/.youtube-shorts-pipeline/media/pipeline_1708512345_en.mp4

  Uploading pipeline_1708512345_en.mp4...
  Upload progress: 100%
  Uploaded: https://youtu.be/xXxXxXxXxXx
  Captions uploaded.

🎉 Done! https://youtu.be/xXxXxXxXxXx
```

Total time: ~3–5 minutes per video on a typical internet connection.

---

## Prerequisites

- **Python 3.10+**
- **ffmpeg** — video assembly
  ```bash
  brew install ffmpeg        # macOS
  apt install ffmpeg         # Ubuntu/Debian
  ```
- **Whisper** — caption generation
  ```bash
  pip install openai-whisper
  ```
- **API accounts:**
  - [Anthropic](https://console.anthropic.com) — Claude (script generation)
  - [ElevenLabs](https://elevenlabs.io) — voiceover *(optional; macOS `say` fallback)*
  - [Google AI Studio](https://aistudio.google.com) — Gemini Imagen (b-roll)
  - [Google Cloud Console](https://console.cloud.google.com) — YouTube Data API v3 (upload)

---

## Quick Start

**1. Install Python dependencies**
```bash
pip install anthropic google-api-python-client google-auth google-auth-oauthlib pillow requests openai-whisper
```

**2. Clone or extract this skill**
```bash
unzip youtube-shorts-pipeline.skill -d youtube-shorts-pipeline
cd youtube-shorts-pipeline
```

**3. Run the pipeline — setup wizard launches automatically**
```bash
python3 scripts/pipeline.py run --news "your topic here" --dry-run
```
The `--dry-run` flag skips produce/upload so you can preview the script first.

**4. Set up YouTube OAuth** *(when ready to upload)*
```bash
python3 scripts/setup_youtube_oauth.py
```
Follow the prompts — you'll need a `client_secret.json` from Google Cloud Console (see [Full Setup](#full-setup)).

**5. Produce and upload**
```bash
python3 scripts/pipeline.py run --news "your topic here"
```

---

## Full Setup

See [`references/setup.md`](references/setup.md) for:
- Step-by-step API key acquisition
- YouTube OAuth setup with Google Cloud Console walkthrough
- Config file reference

---

## Usage

### Draft — generate script and metadata only
```bash
python3 scripts/pipeline.py draft --news "your topic" [--context "esports news channel"]
```
Output: `~/.youtube-shorts-pipeline/drafts/<timestamp>.json`

### Produce — generate video from a saved draft
```bash
python3 scripts/pipeline.py produce --draft ~/.youtube-shorts-pipeline/drafts/<id>.json [--lang en|hi]
```

Override the script inline (after editing the draft):
```bash
python3 scripts/pipeline.py produce --draft <path> --script "Your custom script here."
```

### Upload — push a produced video to YouTube
```bash
python3 scripts/pipeline.py upload --draft ~/.youtube-shorts-pipeline/drafts/<id>.json [--lang en|hi]
```

### Full pipeline in one command
```bash
python3 scripts/pipeline.py run --news "your topic" [--lang en|hi] [--dry-run] [--context "..."]
```

---

## Configuration

On first run, the wizard saves your keys to `~/.youtube-shorts-pipeline/config.json`:

```json
{
  "ANTHROPIC_API_KEY": "YOUR_ANTHROPIC_KEY_HERE",
  "ELEVENLABS_API_KEY": "YOUR_ELEVENLABS_KEY_HERE",
  "GEMINI_API_KEY": "YOUR_GEMINI_KEY_HERE"
}
```

> **Note:** `config.json` is saved with `0600` permissions (owner read/write only). Never commit this file to version control.

**Environment variables take priority** over the config file. You can override any key:
```bash
ANTHROPIC_API_KEY=your-key-here python3 scripts/pipeline.py draft --news "..."
```

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | ✅ Yes | Claude API key |
| `GEMINI_API_KEY` | ✅ Yes | Gemini Imagen API key |
| `ELEVENLABS_API_KEY` | Optional | ElevenLabs TTS key (fallback: macOS `say`) |
| `VOICE_ID_EN` | Optional | ElevenLabs voice ID for English (default: George) |
| `VOICE_ID_HI` | Optional | ElevenLabs voice ID for Hindi |

### Data directories

All data is stored in `~/.youtube-shorts-pipeline/`:

```
~/.youtube-shorts-pipeline/
├── config.json          ← API keys
├── youtube_token.json   ← YouTube OAuth token
├── drafts/
│   └── <timestamp>.json ← draft scripts + metadata
├── media/
│   ├── pipeline_<id>_en.mp4
│   └── pipeline_<id>_en.srt
└── logs/
```

---

## Cost per video

Rough estimates at standard API rates:

| Service | Cost per video |
|---------|---------------|
| Anthropic (Claude Sonnet) | ~$0.02 |
| Google Gemini Imagen (3 images) | ~$0.03 |
| ElevenLabs (60–90 sec audio) | ~$0.05 |
| **Total** | **~$0.10** |

ElevenLabs free tier is blocked on server IPs. Pro plan ($22/mo) is required for non-local use. Gemini and Anthropic have generous free tiers for low-volume use.

---

## Troubleshooting

See [`references/troubleshooting.md`](references/troubleshooting.md) for common errors including:
- YouTube quota errors (`uploadLimitExceeded`, `quotaExceeded`)
- ElevenLabs 401/403 errors
- ffmpeg issues
- Whisper Hindi/Urdu output
- OAuth token expiry

---

## Extending

- **New languages:** Add a `--lang` option and a matching `VOICE_ID_XX` env var. ElevenLabs supports 30+ languages with `eleven_multilingual_v2`.
- **Custom voices:** Change `VOICE_ID_EN` env var to any ElevenLabs voice ID.
- **B-roll style:** Edit the `broll_prompts` array in the saved draft JSON before running `produce`.
- **Script editing:** Use `--script "your edited script"` on the `produce` command.

---

## Security

This pipeline handles API keys and OAuth tokens. The following measures are in place:

- **Credential storage:** `config.json` and `youtube_token.json` are written with `0600` permissions (owner-only). Never commit these files — they are covered by `.gitignore`.
- **API key transmission:** The Gemini API key is sent via the `x-goog-api-key` header, not as a URL query parameter, so it won't leak into logs or error messages.
- **Error handling:** API error messages are sanitized to never include credentials.
- **Upload privacy:** Videos are uploaded as **private** by default. Change to `public` or `unlisted` manually on YouTube when ready.
- **OAuth scope:** YouTube OAuth requests the minimum scopes needed (`youtube.upload` + `youtube.force-ssl`), not full account access.
- **Prompt injection mitigation:** Search result snippets injected into the Claude prompt are truncated and wrapped in boundary markers to reduce prompt injection risk.
- **LLM output validation:** Fields returned by Claude are type-checked before use in metadata and file operations.

---

## Licence

MIT — free to use, modify, and distribute.
Attribution appreciated but not required.
