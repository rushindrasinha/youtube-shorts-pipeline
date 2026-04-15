# Verticals v3

**The open source AI content engine with built in niche intelligence.**

> Topic in. Published Short out. Any niche. ~$0.11 per video.
>
> **[Try it in Google Colab](link) · [Web UI](#web-ui) · [CLI Quickstart](#cli-quickstart) · [Hosted Version](https://verticals.gg)**

```
python -m verticals run --topic "Sam Altman just mass-fired 200 safety researchers" --niche tech
```

That one command researches the topic, writes a hook driven script tuned to tech YouTube, generates cinematic b roll, records a natural voiceover, burns in animated captions, adds mood matched background music, generates a thumbnail, and uploads it to YouTube. ~90 seconds of video, ~3 minutes of wall time, ~$0.11 in API costs.

## What Changed in v3

v2 was an esports news pipeline. v3 is a **general purpose content engine** that works for any niche, any topic, any creator.

The biggest change: **Niche Intelligence**. Every stage of the pipeline now reads from a niche profile that shapes script tone, visual style, caption aesthetics, music mood, and thumbnail strategy. Ship a cooking Short and it writes like a cooking creator, generates food photography b roll, and picks warm upbeat background music. Ship a true crime Short and the tone shifts to suspenseful, the visuals go dark and cinematic, and the music drops to ambient tension.

15 niches ship out of the box. Build your own in 5 minutes.

Other highlights: multi provider LLM support (Claude, Gemini, GPT, Ollama local), free TTS via Edge TTS, stock footage fallback when you don't want AI images, multi platform export (YouTube, TikTok, Reels, X), a Gradio web UI for non developers, and Google Colab for zero install usage.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        NICHE PROFILE                            │
│  Loaded once. Shapes every stage. 15 built in or bring your own │
└─────────────┬───────────────────────────────────────────────────┘
              │
              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ RESEARCH │→ │  SCRIPT  │→ │ VISUALS  │→ │  VOICE   │→ │ CAPTIONS │→ │ ASSEMBLE │→ UPLOAD
│          │  │          │  │          │  │          │  │          │  │          │
│ DuckDuck │  │ LLM with │  │ Gemini   │  │ ElevenLabs│  │ Whisper  │  │ ffmpeg   │
│ Go + web │  │ niche    │  │ Replicate│  │ Edge TTS │  │ word     │  │ Ken Burns│
│ scraping │  │ persona  │  │ Pexels   │  │ Kokoro   │  │ level    │  │ + music  │
│          │  │ + hooks  │  │ ComfyUI  │  │ Bark     │  │ ASS+SRT  │  │ ducking  │
└──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

**Stage by stage:**

**Research** — Searches DuckDuckGo (and optionally scrapes source URLs) for live facts. Every name, number, and claim in the final script traces back to this research. This is the anti hallucination gate: the LLM is instructed to use only facts from research data, never its training knowledge.

**Script** — An LLM (your choice of provider) writes a 60 to 90 second voiceover script using the niche profile's tone, pacing rules, and hook patterns. The profile tells the LLM things like "open with a question, not a statement" for tech niches or "open with a shocking statistic" for finance niches. Output includes the script, b roll image prompts, thumbnail prompt, and platform metadata for YouTube/TikTok/Instagram/X.

**Visuals** — Generates 3 to 5 b roll frames via your configured image provider: Gemini Imagen (default, free tier available), Replicate (Flux, SDXL), or stock footage from Pexels/Pixabay (completely free, no API key needed). Images are auto cropped to 9:16 portrait. The niche profile shapes the visual vocabulary: a fitness niche generates gym and movement imagery, a science niche generates diagrams and lab visuals.

**Voice** — Text to speech via your configured provider: Edge TTS (free, cross platform, 300+ voices, **recommended default**), ElevenLabs (premium, most natural), Kokoro (local, open source), or macOS `say` (fallback). The niche profile suggests voice characteristics (pace, energy, tone) but the final voice selection is yours.

**Captions** — Whisper generates word level timestamps. The pipeline produces both ASS (burned in with word by word yellow highlight) and SRT (uploaded to YouTube for closed captions). Caption styling follows the niche profile: bold energetic fonts for gaming, clean minimal for tech, warm handwritten feel for lifestyle.

**Assemble** — ffmpeg combines animated b roll (Ken Burns zoom/pan effects), voiceover, burned in captions, and background music with automatic voice ducking. Music selection is mood matched to the niche profile.

**Upload** — Publishes to YouTube (private by default) with title, description, tags, SRT captions, and AI generated thumbnail. TikTok and Instagram export coming in v3.1.

## Niche Intelligence

This is what makes Verticals different from every other AI video tool.

A niche profile is a YAML file that tells the pipeline how to think about content for a specific audience. It shapes every stage without requiring any prompt engineering from you.

```yaml
# niches/tech.yaml
name: tech
display_name: "Tech & AI News"

script:
  tone: "informed, slightly opinionated, conversational"
  pacing: "fast, dense with facts, no filler"
  hooks:
    - pattern: "contrarian_take"
      template: "Everyone is celebrating {topic}. Here's why that's a problem."
    - pattern: "breaking_news"
      template: "This just happened and nobody is talking about it."
    - pattern: "prediction"
      template: "{topic} changes everything. Here's what happens next."
    - pattern: "explainer"
      template: "Let me explain {topic} in 60 seconds because most people are getting this wrong."
    - pattern: "comparison"
      template: "{thing_a} vs {thing_b}. One of these wins and it's not even close."
  cta_variants:
    - "Follow for daily tech breakdowns."
    - "Subscribe. I cover AI news nobody else is talking about."
    - "Drop a comment: do you agree?"
  word_count: "150 to 170"
  forbidden: ["like and subscribe", "smash that bell", "what's up guys"]

visuals:
  style: "clean, minimal, dark backgrounds, neon accents"
  mood: "futuristic, sleek, professional"
  subjects:
    [
      "circuit boards",
      "code on screens",
      "server rooms",
      "product shots",
      "data visualizations",
    ]
  avoid: ["stock photo people smiling at laptops", "generic office", "clipart"]

voice:
  pace: "slightly fast, ~160 wpm"
  energy: "confident, authoritative but not robotic"
  suggested_voices:
    edge_tts: "en-US-GuyNeural"
    elevenlabs: "JBFqnCBsd6RMkjVDRZzb"

captions:
  highlight_color: "#00FF88"
  font_weight: "bold"
  position: "lower_third"

music:
  mood: "ambient electronic, subtle energy, no lyrics"
  energy: "medium"

thumbnail:
  style: "dark background, bold white/green text, product or face focus"
  text_position: "left_aligned"
```

**15 built in niches:** tech, gaming, finance, fitness, cooking, travel, true_crime, science, politics, entertainment, sports, fashion, education, motivation, comedy.

**Build your own** by copying any profile and editing it. Drop the YAML in `niches/` and reference it with `--niche your_niche_name`.

## Quickstart

### Option A: Google Colab (zero install)

Open the [Colab notebook](link), paste your API keys, pick a niche, enter a topic, click Run. Done.

### Option B: Web UI (Gradio)

```bash
git clone https://github.com/rushindrasinha/verticals.git
cd verticals
pip install -r requirements.txt
python -m verticals ui
```

Opens a browser UI at `localhost:7860`. Pick a niche, enter a topic, click Generate. Preview the draft before producing.

### Option C: CLI (developers)

```bash
git clone https://github.com/rushindrasinha/verticals.git
cd verticals
pip install -r requirements.txt

# First run triggers setup wizard (API keys)
python -m verticals run --topic "your topic" --niche tech
```

## CLI Commands

### Full pipeline (topic to published Short)

```bash
python -m verticals run --topic "headline" --niche tech
python -m verticals run --topic "headline" --niche cooking --provider ollama
python -m verticals run --discover --niche gaming --auto-pick
```

### Individual stages

```bash
python -m verticals draft --topic "headline" --niche tech
python -m verticals produce --draft <path> --lang en
python -m verticals upload --draft <path> --platform youtube
python -m verticals topics --niche tech --limit 20
```

### Useful flags

```
--niche NAME         Niche profile (default: general)
--provider NAME      LLM provider: claude, gemini, openai, ollama (default: claude)
--voice NAME         TTS provider: edge, elevenlabs, kokoro, say (default: edge)
--visuals NAME       Image provider: gemini, replicate, pexels, comfyui (default: gemini)
--platform NAME      Upload target: youtube, tiktok, reels, x (default: youtube)
--lang CODE          Language: en, hi, es, pt, de, fr, ja, ko (default: en)
--dry-run            Draft only, skip produce and upload
--force              Redo all stages even if completed
--verbose            Debug logging
```

## Provider Support

### LLM (script generation)

| Provider               | Cost                | Setup                       | Notes                                       |
| ---------------------- | ------------------- | --------------------------- | ------------------------------------------- |
| **Claude** (Anthropic) | ~$0.02/script       | `ANTHROPIC_API_KEY`         | Best quality. Default.                      |
| **Gemini** (Google)    | Free tier available | `GEMINI_API_KEY`            | Good quality, generous free tier.           |
| **GPT** (OpenAI)       | ~$0.01/script       | `OPENAI_API_KEY`            | Solid alternative.                          |
| **Ollama** (local)     | Free                | Install Ollama + pull model | No API key needed. Quality varies by model. |
| **Claude CLI**         | Free w/ Max sub     | Install Claude Code         | Uses Claude Max subscription, no API key.   |

### TTS (voiceover)

| Provider       | Cost         | Setup                | Notes                                                 |
| -------------- | ------------ | -------------------- | ----------------------------------------------------- |
| **Edge TTS**   | Free         | None                 | **Recommended default.** 300+ voices, cross platform. |
| **ElevenLabs** | ~$0.05/video | `ELEVENLABS_API_KEY` | Most natural. Premium.                                |
| **Kokoro**     | Free         | `pip install kokoro` | Local, open source.                                   |
| **macOS say**  | Free         | macOS only           | Basic fallback.                                       |

### Visuals (b roll)

| Provider          | Cost                | Setup                  | Notes                              |
| ----------------- | ------------------- | ---------------------- | ---------------------------------- |
| **Gemini Imagen** | Free tier available | `GEMINI_API_KEY`       | Default. Good quality.             |
| **Replicate**     | ~$0.01/image        | `REPLICATE_API_TOKEN`  | Flux, SDXL, more models.           |
| **Pexels**        | Free                | `PEXELS_API_KEY`       | Stock footage. No generation.      |
| **ComfyUI**       | Free (local GPU)    | Running ComfyUI server | Best quality if you have hardware. |

### Upload

| Platform            | Status | Auth                 |
| ------------------- | ------ | -------------------- |
| **YouTube**         | Stable | OAuth (setup wizard) |
| **TikTok**          | v3.1   | Coming soon          |
| **Instagram Reels** | v3.1   | Coming soon          |
| **X (Twitter)**     | v3.1   | Coming soon          |

## $0.00 Mode (completely free)

Yes, you can run this with zero API spend:

```bash
python -m verticals run \
  --topic "your topic" \
  --niche tech \
  --provider ollama \
  --voice edge \
  --visuals pexels
```

Uses Ollama (local LLM), Edge TTS (free Microsoft voices), and Pexels (free stock footage). You need a machine that can run a 7B+ parameter model and a free Pexels API key. Quality is lower than the full API stack but it works.

## Configuration

All keys stored in `~/.verticals/config.json` with 0600 permissions:

| Variable              | Required                    | Used By             |
| --------------------- | --------------------------- | ------------------- |
| `ANTHROPIC_API_KEY`   | If using Claude             | Script generation   |
| `GEMINI_API_KEY`      | If using Gemini visuals/LLM | B roll + thumbnails |
| `OPENAI_API_KEY`      | If using GPT                | Script generation   |
| `ELEVENLABS_API_KEY`  | If using ElevenLabs         | Premium voiceover   |
| `REPLICATE_API_TOKEN` | If using Replicate          | B roll images       |
| `PEXELS_API_KEY`      | If using Pexels             | Stock footage       |

Environment variables override config file values.

## Topic Discovery

Discover trending topics from multiple sources, filtered by niche relevance:

```bash
python -m verticals topics --niche tech --limit 20
```

| Source           | Method      | Auth     | Niche Filtering              |
| ---------------- | ----------- | -------- | ---------------------------- |
| Reddit           | `.json` API | None     | Subreddit mapping per niche  |
| RSS              | feedparser  | None     | Configurable feeds per niche |
| Google Trends    | pytrends    | None     | Geo + category filtering     |
| Twitter/X        | Public API  | Optional | Keyword filtering            |
| TikTok           | Apify       | Optional | Hashtag mapping              |
| YouTube Trending | RSS/API     | None     | Category mapping             |
| Hacker News      | API         | None     | Tech/startup default         |

Configure per niche in your profile:

```yaml
# In niches/tech.yaml
discovery:
  reddit: ["technology", "artificial", "MachineLearning", "singularity"]
  rss: ["https://hnrss.org/frontpage", "https://techcrunch.com/feed"]
  google_trends_category: "t"
  youtube_trending_category: "28"
```

## Cost Per Video

| Configuration                              | Cost   |
| ------------------------------------------ | ------ |
| **Premium** (Claude + Gemini + ElevenLabs) | ~$0.11 |
| **Budget** (Gemini + Gemini + Edge TTS)    | ~$0.04 |
| **Free** (Ollama + Pexels + Edge TTS)      | $0.00  |

## Project Structure

```
verticals/
├── verticals/
│   ├── __main__.py            # CLI + Gradio UI entry point
│   ├── config.py              # Keys, paths, setup wizard
│   ├── niche.py               # Niche profile loader
│   ├── providers/
│   │   ├── llm.py             # Claude / Gemini / GPT / Ollama
│   │   ├── tts.py             # ElevenLabs / Edge / Kokoro / say
│   │   ├── image.py           # Gemini / Replicate / Pexels / ComfyUI
│   │   └── upload.py          # YouTube / TikTok / Reels / X
│   ├── stages/
│   │   ├── research.py        # DuckDuckGo + web scraping
│   │   ├── draft.py           # Script generation with niche intelligence
│   │   ├── broll.py           # Image generation + Ken Burns
│   │   ├── voiceover.py       # TTS with niche voice config
│   │   ├── captions.py        # Whisper + ASS/SRT
│   │   ├── music.py           # Track selection + ducking
│   │   ├── assemble.py        # ffmpeg final assembly
│   │   └── thumbnail.py       # Thumbnail generation + text overlay
│   ├── topics/                # Multi source topic engine
│   ├── state.py               # Resume capability
│   ├── retry.py               # Exponential backoff
│   └── log.py                 # Structured logging
├── niches/                    # 15 built in niche profiles
│   ├── tech.yaml
│   ├── gaming.yaml
│   ├── finance.yaml
│   ├── fitness.yaml
│   ├── cooking.yaml
│   ├── travel.yaml
│   ├── true_crime.yaml
│   ├── science.yaml
│   ├── politics.yaml
│   ├── entertainment.yaml
│   ├── sports.yaml
│   ├── fashion.yaml
│   ├── education.yaml
│   ├── motivation.yaml
│   ├── comedy.yaml
│   └── general.yaml           # Default fallback
├── music/                     # Bundled royalty free tracks
├── ui/                        # Gradio web interface
├── tests/
├── notebooks/
│   └── verticals_colab.ipynb   # Google Colab notebook
├── docker-compose.yml
├── Dockerfile
├── scripts/
│   └── setup_youtube_oauth.py
├── references/
│   ├── setup.md
│   └── troubleshooting.md
├── pyproject.toml
└── requirements.txt
```

## Testing

```bash
pip install pytest pytest-mock
python -m pytest tests/ -v
```

## Docker

```bash
docker compose up --build
# Opens web UI at localhost:7860
```

## Security

All security measures from v2 carry forward, plus:

**Credential storage:** Config and tokens use 0600 permissions via atomic `os.open()`.
**API key handling:** All providers send keys via headers, never URL parameters.
**Upload privacy:** YouTube uploads default to private.
**Prompt injection:** Research snippets truncated to 300 chars with boundary markers. LLM output fields are type checked before use.
**OAuth scopes:** Minimum required scopes per platform.
**Niche profiles:** YAML parsed with safe_load (no code execution).
**Dependency pinning:** Compatible release bounds on all packages.

## Roadmap

**v3.0** (this release)
Niche intelligence, multi provider LLM/TTS/image, Gradio UI, Colab notebook, Edge TTS default, Pexels stock footage, Docker support

**v3.1** (planned)
TikTok/Instagram/X upload, multi language niche profiles, A/B script variants (generate 2, pick better), scheduled batch production

**v3.2** (planned)
Analytics integration (which Shorts performed best), niche profile auto tuning based on performance data, series support (multi episode narrative arcs)

## Built By

**[Dr Rushindra Sinha](https://github.com/rushindrasinha)** — MD, Stanford GSB, Full Stack Developer.

Built the first game server at 17 (went #1 globally, acquired before finishing med school). Co-founded [Global Esports](https://globalesports.in) — South Asia's only Valorant Champions Tour Pacific franchise. Now building AI tools for creators and operators at [aarees.com](https://aarees.com).

Follow: [@irushi](https://twitter.com/irushi) on X · [@rushindrasinha](https://instagram.com/rushindrasinha) on Instagram

---

## More From This Stack

| Product                                        | What it does                                                                           |
| ---------------------------------------------- | -------------------------------------------------------------------------------------- |
| [**verticals.gg**](https://verticals.gg)       | Hosted version of this pipeline — no setup, no terminal, just results                  |
| [**thumbnail.gg**](https://thumbnail.gg)       | AI thumbnail generation with deep niche intelligence and CTR optimization              |
| [**aarees.com**](https://aarees.com)           | The AI agent platform powering both products                                           |
| [**Global Esports**](https://globalesports.in) | South Asia's VCT Pacific franchise — where the esports niche profile was battle-tested |

---

## License

MIT
