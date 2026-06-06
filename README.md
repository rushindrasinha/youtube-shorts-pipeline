# Verticals v3

**The open source AI content engine with built-in niche intelligence.**

> Topic in. Published Short out. Any niche. ~$0.11 per video.
>
> **[Quickstart](#quickstart) · [Hosted Version](https://verticals.gg)**

> Repo note: the product is called **Verticals v3**. The GitHub repository is `youtube-shorts-pipeline`.

```bash
python -m verticals run --topic "Sam Altman just mass-fired 200 safety researchers" --niche tech
```

That one command researches the topic, writes a hook-driven script tuned to the niche, generates cinematic b-roll, records a natural voiceover, burns in animated captions, adds mood-matched background music, generates a thumbnail, and uploads it to YouTube — private by default. ~90 seconds of video, ~3 minutes of wall time, ~$0.11 in API costs.

---

## Table of Contents

- [What This Repo Does](#what-this-repo-does)
- [How It Works](#how-it-works)
- [Niche Intelligence](#niche-intelligence)
- [Quickstart](#quickstart)
- [Secrets & API Keys — Full Setup](#secrets--api-keys--full-setup)
- [YouTube OAuth Setup](#youtube-oauth-setup)
- [Where Your Finished Video Ends Up](#where-your-finished-video-ends-up)
- [CLI Commands](#cli-commands)
- [Provider Support](#provider-support)
- [Cost Per Video](#cost-per-video)
- [Topic Discovery](#topic-discovery)
- [Project Structure](#project-structure)
- [Roadmap](#roadmap)

---

## What This Repo Does

Verticals v3 is a **general-purpose AI short-form video pipeline**. Give it a topic and a niche — it handles everything from research to YouTube upload with no manual editing.

**6 custom channel profiles ship in this repo:**

| File | Channel | Niche |
|------|---------|-------|
| `dopamine_loop.yaml` | **Dopamine Loop** | Psychology / Celebrity / Self-improvement |
| `finance_fiction.yaml` | **FinanceFiction** | Finance psychology / Behavioral economics |
| `redacted.yaml` | **REDACTED** | Declassified ops / Hidden history |
| `grey_matter.yaml` | **The Grey Matter** | Neuroscience |
| `quiet_record.yaml` | **The Quiet Record** | Forgotten history / Archival recovery |
| `red_space_facts.yaml` | **Red Space Facts** | Space facts / Astronomy / Cosmic scale |

Build your own in 5 minutes by copying any `.yaml` and dropping it in `niches/`.

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        NICHE PROFILE                            │
│  Loaded once. Shapes every stage. 21 built-in or bring your own │
└─────────────┬───────────────────────────────────────────────────┘
              │
              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ RESEARCH │→ │  SCRIPT  │→ │ VISUALS  │→ │  VOICE   │→ │ CAPTIONS │→ │ ASSEMBLE │→ UPLOAD
│          │  │          │  │          │  │          │  │          │  │          │
│ DuckDuck │  │ LLM with │  │ Gemini   │  │ ElevenLabs│  │ Whisper  │  │ ffmpeg   │
│ Go + web │  │ niche    │  │ fallback │  │ Edge TTS │  │ word     │  │ Ken Burns│
│ scraping │  │ persona  │  │ frames   │  │ say      │  │ level    │  │ + music  │
│          │  │ + hooks  │  │          │  │          │  │ ASS+SRT  │  │ ducking  │
└──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

**Research** — Searches DuckDuckGo (and optionally scrapes source URLs) for live facts. Every claim in the script traces back to this research. The LLM is instructed to use only research data, never training knowledge.

**Script** — An LLM writes a 60–90 second voiceover script using the niche profile's tone, pacing rules, and hook patterns. Output includes the script, b-roll image prompts, thumbnail prompt, and platform metadata.

**Visuals** — Generates 3 b-roll frames via Gemini Imagen, then auto-crops to 9:16 portrait. Falls back to solid-color frames if generation fails.

**Voice** — Text-to-speech via Edge TTS (free, recommended), ElevenLabs (premium), or macOS `say`.

**Captions** — Whisper generates word-level timestamps. Produces ASS (burned-in, word-by-word highlight) and SRT (uploaded to YouTube).

**Assemble** — ffmpeg combines animated b-roll (Ken Burns zoom/pan), voiceover, burned-in captions, and mood-matched background music with automatic voice ducking.

**Upload** — Publishes to YouTube (private by default) with title, description, tags, SRT captions, and AI-generated thumbnail.

---

## Niche Intelligence

A niche profile is a YAML file that tells the pipeline how to think for a specific audience. It shapes every stage without any prompt engineering from you.

```yaml
# niches/finance.yaml (example)
name: finance
script:
  tone: "clear, data driven, authoritative but accessible"
  hooks:
    - id: statistic_shock
      template: "{shocking_stat}. And most people have no idea what this means for their money."
      when: "surprising market data"
  cta_variants:
    - "Follow for daily market breakdowns."
  word_count: "140 to 165"
visuals:
  style: "dark backgrounds, green/red accents, clean data aesthetic"
  color_palette: ["#0D1117", "#00C853", "#FF1744"]
voice:
  pace: "moderate, approximately 145 words per minute"
  suggested_voices:
    edge_tts:
      en: "en-US-GuyNeural"
captions:
  highlight_color: "#00C853"
music:
  mood: "ambient, subtle tension, no lyrics"
  duck_volume_speech: 0.10
thumbnail:
  style: "dark background, bold numbers, red/green accent"
discovery:
  reddit:
    subreddits: ["personalfinance", "investing", "economics"]
  rss:
    feeds:
      - "https://feeds.bloomberg.com/markets/news.rss"
```

Drop any `.yaml` in `niches/` and reference it with `--niche your_name`.

---

## Quickstart

```bash
git clone https://github.com/chileleko366-stack/youtube-shorts-pipeline.git
cd youtube-shorts-pipeline
pip install -r requirements.txt

python -m verticals run --topic "your topic" --niche tech
```

First run triggers an interactive setup wizard that asks for your API keys and walks through YouTube OAuth. After that first run, every subsequent command works without any prompts.

---

## Secrets & API Keys — Full Setup

All keys are stored in `~/.verticals/config.json` with `0600` permissions (owner read/write only). Never commit this file. Environment variables override config file values.

### Required to generate video

| Key | Used For | Where to Get It | Free? |
|-----|----------|-----------------|-------|
| `ANTHROPIC_API_KEY` | Script generation (default LLM) | [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) → Create key | Pay-as-you-go (~$0.02/script) |
| `GEMINI_API_KEY` | B-roll image generation + optional LLM | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) → Create key | Free tier available |

### Required to upload to YouTube

YouTube upload uses OAuth — not an API key. Setup is a one-time flow:

1. Create a Google Cloud project and enable **YouTube Data API v3** — [console.cloud.google.com](https://console.cloud.google.com)
2. Create an **OAuth 2.0 Client ID** (Desktop app type) and download the JSON
3. Run `python scripts/setup_youtube_oauth.py` — it opens a browser, you sign in, token saved to `~/.verticals/youtube_token.json`

Full walkthrough: [YouTube OAuth Setup](#youtube-oauth-setup)

### Optional (upgrade quality or change provider)

| Key | Used For | Where to Get It | Cost |
|-----|----------|-----------------|------|
| `ELEVENLABS_API_KEY` | Premium realistic voiceover | [elevenlabs.io/settings/api-keys](https://elevenlabs.io/settings/api-keys) | ~$0.05/video (Pro plan required for non-local use — $22/mo) |
| `OPENAI_API_KEY` | Use GPT instead of Claude for scripts | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | ~$0.01/script |

### Zero-key path (completely free)

```bash
# Use Ollama (local LLM) for script, Edge TTS (free) for voice
python -m verticals run --topic "your topic" --niche tech --provider ollama --voice edge
```

You still need `GEMINI_API_KEY` for b-roll image generation. If you skip that too, the pipeline uses solid-color fallback frames.

### Config file reference

After setup, your `~/.verticals/config.json` looks like:

```json
{
  "ANTHROPIC_API_KEY": "sk-ant-...",
  "GEMINI_API_KEY": "AIza...",
  "ELEVENLABS_API_KEY": "sk_...",
  "OPENAI_API_KEY": "sk-..."
}
```

---

## GitHub Actions Secrets (for automated daily runs)

The workflow at `.github/workflows/daily_shorts.yml` runs all 6 channels twice a day automatically. It needs **2 GitHub repository secrets** — not environment variables, not config files. Add them at:

**GitHub repo → Settings → Secrets and variables → Actions → New repository secret**

| Secret name | What it contains | How to get it |
|-------------|-----------------|---------------|
| `VERTICALS_CONFIG` | The full contents of your `~/.verticals/config.json` as a single JSON string | Run the pipeline locally once, then `cat ~/.verticals/config.json` and paste the output |
| `YOUTUBE_TOKEN` | The full contents of your `~/.verticals/youtube_token.json` as a single JSON string | Run `python scripts/setup_youtube_oauth.py` locally, then `cat ~/.verticals/youtube_token.json` and paste the output |

**`VERTICALS_CONFIG` example value** (paste the whole thing as the secret):
```json
{"ANTHROPIC_API_KEY":"sk-ant-...","GEMINI_API_KEY":"AIza..."}
```

**`YOUTUBE_TOKEN` example value** (paste the whole thing as the secret):
```json
{"token":"ya29...","refresh_token":"1//...","token_uri":"https://oauth2.googleapis.com/token","client_id":"...","client_secret":"...","scopes":["https://www.googleapis.com/auth/youtube.upload","https://www.googleapis.com/auth/youtube.force-ssl"]}
```

Once both secrets are set, the workflow triggers automatically at **8 AM UTC** (morning) and **6 PM UTC** (evening) every day — producing 1 Short per channel per run, 2 Shorts per channel per day across all 6 channels.

You can also trigger a single run manually from **GitHub → Actions → Daily Shorts — All Channels → Run workflow**, with an optional niche filter to run just one channel.

---

## YouTube OAuth Setup

One-time setup. You need a Google account with a YouTube channel.

**Step 1 — Enable the API**
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or select an existing one)
3. Go to **APIs & Services → Library**
4. Search for **YouTube Data API v3** and click **Enable**

**Step 2 — Create OAuth credentials**
1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth 2.0 Client ID**
3. Application type: **Desktop app**
4. Name it anything, click **Create**, then **Download JSON**
5. Save the file as `client_secret.json` somewhere on your machine

**Step 3 — Authorize**
```bash
python scripts/setup_youtube_oauth.py
```

The script asks for the path to your `client_secret.json`, opens a browser tab for Google sign-in, and saves the token to `~/.verticals/youtube_token.json`. Scopes: `youtube.upload` + `youtube.force-ssl` (minimum needed for upload and captions).

You only do this once. The token auto-refreshes.

---

## Where Your Finished Video Ends Up

### On disk

Every run creates a numbered draft folder at `~/.verticals/drafts/<id>/`:

```
~/.verticals/drafts/
└── 20240610_143022_tech/
    ├── draft.json              ← script, metadata, prompts
    ├── research.json           ← raw research data
    ├── broll_0.png             ← b-roll frame 1
    ├── broll_1.png             ← b-roll frame 2
    ├── broll_2.png             ← b-roll frame 3
    ├── voiceover.mp3           ← generated voiceover
    ├── captions.ass            ← burned-in caption file
    ├── captions.srt            ← SRT for YouTube upload
    ├── thumbnail.png           ← AI-generated thumbnail
    └── final.mp4               ← THE FINISHED VIDEO ← this is your Short
```

**`final.mp4` is your finished product.** 9:16 portrait, ~60–90 seconds, captions burned in, music mixed.

### On YouTube

After `upload` runs, the video is published to your YouTube channel as **private by default**. You can review it in YouTube Studio before making it public. The upload includes:

- Title, description, and tags (AI-generated from the script)
- SRT captions (uploaded separately as a closed caption track)
- Thumbnail (the `thumbnail.png` from the draft folder)
- Category and language metadata

To find it: [YouTube Studio](https://studio.youtube.com) → **Content** → look for your video with a lock icon (private).

### Changing upload visibility

To publish as unlisted or public, add `--visibility` (coming v3.1), or flip it manually in YouTube Studio after upload.

---

## CLI Commands

### Full pipeline (topic to published Short)
```bash
python -m verticals run --topic "headline" --niche tech
python -m verticals run --topic "headline" --niche dopamine_loop --provider claude
python -m verticals run --discover --niche red_space_facts --auto-pick
```

### Individual stages
```bash
python -m verticals draft --topic "headline" --niche grey_matter
python -m verticals produce --draft <path>
python -m verticals upload --draft <path>
python -m verticals topics --niche quiet_record --limit 20
```

### Useful flags
```
--niche NAME         Niche profile (default: general)
--provider NAME      LLM provider: claude, gemini, openai, ollama (default: claude)
--voice NAME         TTS provider: edge, elevenlabs, say (default: edge)
--platform NAME      Draft target: shorts, reels, tiktok, all (default: shorts)
--lang CODE          Language: en, hi, es, pt, de, fr, ja, ko (default: en)
--dry-run            Draft only, skip produce and upload
--force              Redo all stages even if completed
--verbose            Debug logging
```

---

## Provider Support

### LLM (script generation)

| Provider | Cost | Setup | Notes |
|----------|------|-------|-------|
| **Claude** (Anthropic) | ~$0.02/script | `ANTHROPIC_API_KEY` | Best quality. Default. |
| **Gemini** (Google) | Free tier available | `GEMINI_API_KEY` | Good quality, generous free tier. |
| **GPT** (OpenAI) | ~$0.01/script | `OPENAI_API_KEY` | Solid alternative. |
| **Ollama** (local) | Free | Install Ollama + pull model | No API key. Quality varies. |
| **Claude CLI** | Free w/ Max sub | Install Claude Code | Uses Claude Max subscription. |

### TTS (voiceover)

| Provider | Cost | Setup | Notes |
|----------|------|-------|-------|
| **Edge TTS** | Free | None | **Recommended default.** 300+ voices, cross-platform. |
| **ElevenLabs** | ~$0.05/video | `ELEVENLABS_API_KEY` | Most natural. Pro plan required for server use. |
| **macOS say** | Free | macOS only | Basic fallback. |

### Visuals (b-roll)

| Provider | Cost | Setup | Notes |
|----------|------|-------|-------|
| **Gemini Imagen** | Free tier available | `GEMINI_API_KEY` | Default image provider. |
| **Fallback frames** | Free | None | Solid-color frames if generation fails. |

### Upload

| Platform | Status | Auth |
|----------|--------|------|
| **YouTube** | Stable | OAuth (one-time setup wizard) |
| **TikTok** | v3.1 | Coming soon |
| **Instagram Reels** | v3.1 | Coming soon |
| **X (Twitter)** | v3.1 | Coming soon |

---

## Cost Per Video

| Configuration | Cost |
|---------------|------|
| **Premium** (Claude + Gemini Imagen + ElevenLabs) | ~$0.11 |
| **Budget** (Gemini LLM + Gemini Imagen + Edge TTS) | ~$0.04 |
| **Draft-only local** (Ollama, no video) | $0.00 |
| **Full free** (Ollama + Edge TTS, fallback frames) | $0.00 |

---

## Topic Discovery

Discover trending topics from multiple sources, filtered by niche:

```bash
python -m verticals topics --niche redacted --limit 20
```

| Source | Method | Auth |
|--------|--------|------|
| Reddit | `.json` API | None |
| RSS | feedparser | None |
| Google Trends | pytrends | None |
| Hacker News | API | None |

Discovery sources are configured per niche in the YAML profile under `discovery.reddit.subreddits` and `discovery.rss.feeds`.

---

## Project Structure

```
youtube-shorts-pipeline/
├── verticals/
│   ├── __main__.py            # CLI entry point
│   ├── config.py              # Keys, paths, setup wizard
│   ├── niche.py               # Niche profile loader
│   ├── llm.py                 # Claude / Gemini / GPT / Ollama
│   ├── research.py            # DuckDuckGo research gate
│   ├── draft.py               # Script generation with niche intelligence
│   ├── broll.py               # Gemini image generation + Ken Burns
│   ├── tts.py                 # ElevenLabs / Edge / say
│   ├── captions.py            # Whisper + ASS/SRT
│   ├── music.py               # Track selection + ducking
│   ├── assemble.py            # ffmpeg final assembly
│   ├── thumbnail.py           # Thumbnail generation + text overlay
│   ├── upload.py              # YouTube upload
│   ├── topics/                # Multi-source topic engine
│   ├── state.py               # Resume capability
│   ├── retry.py               # Exponential backoff
│   └── log.py                 # Structured logging
├── niches/                    # 6 custom channel profiles
│   ├── dopamine_loop.yaml     # Psychology / Celebrity / Self-improvement
│   ├── finance_fiction.yaml   # Finance psychology / Behavioral economics
│   ├── redacted.yaml          # Declassified ops / Hidden history
│   ├── grey_matter.yaml       # Neuroscience
│   ├── quiet_record.yaml      # Forgotten history / Archival recovery
│   └── red_space_facts.yaml   # Space facts / Astronomy / Cosmic scale
├── scripts/
│   └── setup_youtube_oauth.py
├── references/
│   ├── setup.md
│   └── troubleshooting.md
├── tests/
├── pyproject.toml
└── requirements.txt
```

---

## Testing

```bash
pip install -e ".[dev]"
python -m pytest tests/ -q
```

---

## Roadmap

**v3.0** (current)
  Niche intelligence, multi-provider LLM, Edge TTS default, topic discovery, resumable stages, YouTube upload

**v3.1** (planned)
  TikTok/Instagram/X upload, multi-language niche profiles, A/B script variants, scheduled batch production, upload visibility flag

**v3.2** (planned)
  Analytics integration, niche profile auto-tuning based on performance data, series support

**Later**
  Web UI, Docker, Google Colab, additional visual providers, stock footage fallback

---

## Security

- Credentials stored at `~/.verticals/config.json` with `0600` permissions via atomic `os.open()`
- API keys sent via headers only, never URL parameters
- YouTube uploads default to private
- Research snippets truncated to 300 chars with boundary markers to prevent prompt injection
- OAuth uses minimum required scopes
- YAML profiles parsed with `safe_load` (no code execution)
- All package versions pinned with compatible release bounds

---

## Built By

**[Dr Rushindra Sinha](https://github.com/rushindrasinha)** — MD, Stanford GSB, Full Stack Developer.

Built the first game server at 17 (went #1 globally, acquired before finishing med school). Co-founded [Global Esports](https://globalesports.in) — South Asia's only Valorant Champions Tour Pacific franchise. Now building AI tools for creators and operators at [aarees.com](https://aarees.com).

Follow: [@irushi](https://twitter.com/irushi) on X · [@rushindrasinha](https://instagram.com/rushindrasinha) on Instagram

---

## More From This Stack

| Product | What it does |
|---------|-------------|
| [**verticals.gg**](https://verticals.gg) | Hosted version of this pipeline — no setup, no terminal, just results |
| [**thumbnail.gg**](https://thumbnail.gg) | AI thumbnail generation with deep niche intelligence and CTR optimization |
| [**aarees.com**](https://aarees.com) | The AI agent platform powering both products |
| [**Global Esports**](https://globalesports.in) | South Asia's VCT Pacific franchise |

---

## License

MIT
