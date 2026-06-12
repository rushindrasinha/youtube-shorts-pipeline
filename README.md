# Verticals v3

**The open source AI content engine with built-in niche intelligence.**

> Topic in. Published Short out. Any niche. ~$0.11 per video.
>
> **[Quickstart](#quickstart) · [Hosted Version](https://verticals.gg)**

> Repo note: the product is called **Verticals v3**. The GitHub repository is `youtube-shorts-pipeline`.

```
python -m verticals run --topic "Sam Altman just mass-fired 200 safety researchers" --niche tech
```

---

<p align="center">
  <a href="https://www.atlascloud.ai/?utm_source=github&utm_medium=link&utm_campaign=youtube-shorts-pipeline">
    <img src="./docs/atlas-cloud-logo.png" alt="Atlas Cloud" width="200">
  </a>
</p>

> 🎁 **[Atlas Cloud](https://www.atlascloud.ai/?utm_source=github&utm_medium=link&utm_campaign=youtube-shorts-pipeline)** is a full-modal AI inference platform that gives developers a single AI API to access video generation, image generation, and LLM APIs. Instead of managing multiple vendor integrations, you connect once and get unified access to 300+ curated models across all modalities.
>
> This pipeline touches both halves of Atlas Cloud at once: the **script** stage needs an LLM, and the **visuals/thumbnail** stages need image generation. With Atlas Cloud you point both at one key. Its LLM endpoint is OpenAI-compatible, so the `openai` provider works out of the box:
>
> ```bash
> export OPENAI_BASE_URL="https://api.atlascloud.ai/v1"
> export OPENAI_API_KEY="<your Atlas Cloud key>"
> export OPENAI_MODEL="deepseek-ai/deepseek-v4-pro"   # or any LLM from the list below
> python -m verticals run --topic "your topic" --niche tech --provider openai
> ```
>
> `deepseek-ai/deepseek-v4-pro` is a reasoning model — give it enough `max_tokens` (>= 512), otherwise the budget can be spent on the chain-of-thought and you get an empty `content` with `finish_reason=length`. (Verticals' script stage already requests a generous token budget.)
>
> Check out Atlas Cloud's coding plan for more budget-friendly API access: <https://www.atlascloud.ai/console/coding-plan>

<details>
<summary><strong>Atlas Cloud model catalog (LLM + image/video)</strong></summary>

**LLM** (OpenAI-compatible, set as `OPENAI_MODEL`). Recommended default: `deepseek-ai/deepseek-v4-pro`. Full official list (59 models, synced with <https://www.atlascloud.ai/zh/models/list/llm>):

- Anthropic (Claude): `anthropic/claude-haiku-4.5-20251001`, `anthropic/claude-opus-4.8`, `anthropic/claude-sonnet-4.6`
- OpenAI (GPT): `openai/gpt-5.4`, `openai/gpt-5.5`
- Google (Gemini): `google/gemini-3.1-flash-lite`, `google/gemini-3.1-pro-preview`, `google/gemini-3.5-flash`
- Alibaba (Qwen): `qwen/qwen2.5-7b-instruct`, `Qwen/Qwen3-235B-A22B-Instruct-2507`, `qwen/qwen3-235b-a22b-thinking-2507`, `qwen/qwen3-30b-a3b`, `Qwen/Qwen3-30B-A3B-Instruct-2507`, `qwen/qwen3-30b-a3b-thinking-2507`, `qwen/qwen3-32b`, `qwen/qwen3-8b`, `Qwen/Qwen3-Coder`, `qwen/qwen3-coder-next`, `qwen/qwen3-max-2026-01-23`, `Qwen/Qwen3-Next-80B-A3B-Instruct`, `Qwen/Qwen3-Next-80B-A3B-Thinking`, `Qwen/Qwen3-VL-235B-A22B-Instruct`, `qwen/qwen3-vl-235b-a22b-thinking`, `qwen/qwen3-vl-30b-a3b-instruct`, `qwen/qwen3-vl-30b-a3b-thinking`, `qwen/qwen3-vl-8b-instruct`, `qwen/qwen3.5-122b-a10b`, `qwen/qwen3.5-27b`, `qwen/qwen3.5-35b-a3b`, `qwen/qwen3.5-397b-a17b`, `qwen/qwen3.6-35b-a3b`, `qwen/qwen3.6-plus`
- DeepSeek: `deepseek-ai/deepseek-ocr`, `deepseek-ai/deepseek-r1-0528`, `deepseek-ai/DeepSeek-V3-0324`, `deepseek-ai/DeepSeek-V3.1`, `deepseek-ai/DeepSeek-V3.1-Terminus`, `deepseek-ai/deepseek-v3.2`, `deepseek-ai/DeepSeek-V3.2-Exp`, `deepseek-ai/deepseek-v4-flash`, `deepseek-ai/deepseek-v4-pro`
- Moonshot (Kimi): `moonshotai/Kimi-K2-Instruct`, `moonshotai/Kimi-K2-Instruct-0905`, `moonshotai/Kimi-K2-Thinking`, `moonshotai/kimi-k2.5`, `moonshotai/kimi-k2.6`
- Zhipu (GLM): `zai-org/GLM-4.6`, `zai-org/glm-4.7`, `zai-org/glm-5`, `zai-org/glm-5-turbo`, `zai-org/glm-5.1`, `zai-org/glm-5v-turbo`
- MiniMax: `MiniMaxAI/MiniMax-M2`, `minimaxai/minimax-m2.1`, `minimaxai/minimax-m2.5`, `minimaxai/minimax-m2.7`
- xAI: `xai/grok-4.3`
- Kuaishou (KAT): `kwaipilot/kat-coder-pro-v2`
- Other: `owl`

**Image / video** (for b-roll, thumbnails, and future video stages). Recommended defaults: image `openai/gpt-image-2/text-to-image`, video `bytedance/seedance-2.0/text-to-video`. A selection from the official model page at <https://www.atlascloud.ai/models>:

- TEXT-TO-IMAGE: `openai/gpt-image-2/text-to-image`, `alibaba/wan-2.7/text-to-image`, `qwen/qwen-image-2.0/text-to-image`, `bytedance/seedream-v4.5`, `google/imagen4`, `google/nano-banana/text-to-image`, `black-forest-labs/flux-2-pro/text-to-image`
- IMAGE-TO-IMAGE: `openai/gpt-image-2/edit`, `alibaba/wan-2.7/image-edit`, `qwen/qwen-image-2.0/edit`, `bytedance/seedream-v4.5/edit`, `google/nano-banana/edit`, `black-forest-labs/flux-kontext-dev`
- TEXT-TO-VIDEO: `bytedance/seedance-2.0/text-to-video`, `bytedance/seedance-2.0-fast/text-to-video`, `alibaba/wan-2.7/text-to-video`, `google/veo3.1/text-to-video`, `kwaivgi/kling-v3.0-pro/text-to-video`
- IMAGE-TO-VIDEO: `bytedance/seedance-2.0/image-to-video`, `bytedance/seedance-2.0-fast/image-to-video`, `alibaba/wan-2.7/image-to-video`, `google/veo3.1/image-to-video`, `kwaivgi/kling-v3.0-pro/image-to-video`

See the full catalog and docs at <https://www.atlascloud.ai/models> and <https://www.atlascloud.ai/docs>.

</details>

---

That one command researches the topic, writes a hook driven script tuned to tech YouTube, generates cinematic b roll, records a natural voiceover, burns in animated captions, adds mood matched background music, generates a thumbnail, and uploads it to YouTube. ~90 seconds of video, ~3 minutes of wall time, ~$0.11 in API costs.

## What Changed in v3

v2 was an esports news pipeline. v3 is a **general purpose content engine** that works for any niche, any topic, any creator.

The biggest change: **Niche Intelligence**. Every stage of the pipeline now reads from a niche profile that shapes script tone, visual style, caption aesthetics, music mood, and thumbnail strategy. Ship a cooking Short and it writes like a cooking creator, generates food photography b roll, and picks warm upbeat background music. Ship a true crime Short and the tone shifts to suspenseful, the visuals go dark and cinematic, and the music drops to ambient tension.

15 niches ship out of the box. Build your own in 5 minutes.

Other highlights: multi provider LLM support (Claude, Gemini, GPT, Ollama local), free TTS via Edge TTS, YouTube upload, topic discovery, resumable stages, and a local-first config model.

## Current Release: v3.1.0

v3.1.0 brings community-contributed providers and reliability fixes: MiniMax (LLM + TTS) and 60db (TTS) as optional providers, niche-aware caption fonts so CJK and other non-Latin scripts render correctly, a working `edge-tts` pin (6.x is rejected by Microsoft with 403s), and clearer errors for the most-reported setup problems.

Implemented today:

- research with DuckDuckGo plus optional source scraping
- script and metadata generation through Claude, Gemini, GPT, Ollama, MiniMax, LiteLLM, or Claude CLI
- b roll and thumbnail image generation through Gemini Imagen, with fallback frames
- voiceover through Edge TTS, ElevenLabs, MiniMax, 60db, or macOS `say`
- Whisper captions with ASS burn-in plus SRT export, niche-configurable fonts
- ffmpeg assembly with Ken Burns motion, background music, and voice ducking
- private-by-default YouTube upload

Not shipped yet: Gradio UI, Docker, Colab, TikTok/Reels/X upload, Pexels, Replicate, ComfyUI, and Kokoro TTS. Those are roadmap items, not current features.

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
│ Go + web │  │ niche    │  │ fallback │  │ Edge TTS │  │ word     │  │ Ken Burns│
│ scraping │  │ persona  │  │ frames   │  │ say      │  │ level    │  │ + music  │
│          │  │ + hooks  │  │          │  │          │  │ ASS+SRT  │  │ ducking  │
└──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘
```

**Stage by stage:**

**Research** — Searches DuckDuckGo (and optionally scrapes source URLs) for live facts. Every name, number, and claim in the final script traces back to this research. This is the anti hallucination gate: the LLM is instructed to use only facts from research data, never its training knowledge.

**Script** — An LLM (your choice of provider) writes a 60 to 90 second voiceover script using the niche profile's tone, pacing rules, and hook patterns. The profile tells the LLM things like "open with a question, not a statement" for tech niches or "open with a shocking statistic" for finance niches. Output includes the script, b roll image prompts, thumbnail prompt, and platform metadata for YouTube/TikTok/Instagram/X.

**Visuals** — Generates 3 b roll frames via Gemini Imagen, then auto crops them to 9:16 portrait. If image generation fails, the pipeline uses simple fallback frames so assembly can still complete. The niche profile shapes the visual vocabulary: a fitness niche generates gym and movement imagery, a science niche generates diagrams and lab visuals.

**Voice** — Text to speech via your configured provider: Edge TTS (free, cross platform, 300+ voices, **recommended default**), ElevenLabs (premium, most natural), or macOS `say` (fallback). The niche profile suggests voice characteristics (pace, energy, tone) but the final voice selection is yours.

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
  subjects: ["circuit boards", "code on screens", "server rooms", "product shots", "data visualizations"]
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

**15 built-in niches plus a general fallback:** tech, gaming, finance, fitness, cooking, travel, true_crime, science, politics, entertainment, sports, fashion, education, motivation, comedy, and general.

**Build your own** by copying any profile and editing it. Drop the YAML in `niches/` and reference it with `--niche your_niche_name`.

## Quickstart

### CLI

```bash
git clone https://github.com/rushindrasinha/youtube-shorts-pipeline.git
cd youtube-shorts-pipeline
pip install -r requirements.txt

python -m verticals run --topic "your topic" --niche tech
```

The old `--news` flag still works for backwards compatibility, but `--topic` is the recommended public API.

### Hosted Version

Use [verticals.gg](https://verticals.gg) if you want the workflow without local setup.

## Examples

Two worked end-to-end examples with real commands and the exact output to expect at each stage live in [`examples/`](examples/):

- [Tech news Short, full pipeline](examples/01-tech-news-short.md) — draft, produce, upload with the default providers
- [Zero-cost draft with topic discovery](examples/02-free-draft-discovery.md) — trending topics plus a local Ollama draft, no paid keys

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
python -m verticals upload --draft <path> --lang en
python -m verticals topics --niche tech --limit 20
```

### Useful flags
```
--niche NAME         Niche profile (default: general)
--provider NAME      LLM provider: claude, gemini, openai, ollama, minimax (default: claude)
--voice NAME         TTS provider: edge, elevenlabs, minimax, 60db, say (default: edge)
--platform NAME      Draft target: shorts, reels, tiktok, all (default: shorts)
--lang CODE          Language: en, hi, es, pt, de, fr, ja, ko (default: en)
--dry-run            Draft only, skip produce and upload
--force              Redo all stages even if completed
--verbose            Debug logging
```

## Provider Support

### LLM (script generation)

| Provider | Cost | Setup | Notes |
|----------|------|-------|-------|
| **Claude** (Anthropic) | ~$0.02/script | `ANTHROPIC_API_KEY` | Best quality. Default. |
| **Gemini** (Google) | Free tier available | `GEMINI_API_KEY` | Good quality, generous free tier. |
| **GPT** (OpenAI) | ~$0.01/script | `OPENAI_API_KEY` | Solid alternative. |
| **[Atlas Cloud](https://www.atlascloud.ai/?utm_source=github&utm_medium=link&utm_campaign=youtube-shorts-pipeline)** | Usage-based | `OPENAI_API_KEY` + `OPENAI_BASE_URL=https://api.atlascloud.ai/v1` | OpenAI-compatible. One key for 300+ LLMs **and** image/video gen. Set `--provider openai`. |
| **Ollama** (local) | Free | Install Ollama + pull model | No API key needed. Quality varies by model. |
| **Claude CLI** | Free w/ Max sub | Install Claude Code | Uses Claude Max subscription, no API key. See [Claude authentication](#claude-authentication). |
| **MiniMax** | Pay-as-you-go | `MINIMAX_API_KEY` | OpenAI-compatible API. |

### TTS (voiceover)

| Provider | Cost | Setup | Notes |
|----------|------|-------|-------|
| **Edge TTS** | Free | None | **Recommended default.** 300+ voices, cross platform. |
| **ElevenLabs** | ~$0.05/video | `ELEVENLABS_API_KEY` | Most natural. Premium. |
| **MiniMax** | Pay-as-you-go | `MINIMAX_API_KEY` | Streaming TTS, English voices. |
| **60db** | Pay-as-you-go | `SIXTYDB_API_KEY` | Native Indic-language voices, low per-character cost. List voices: `python -m verticals voices --provider 60db`. |
| **macOS say** | Free | macOS only | Basic fallback. |

### Claude authentication

The `claude` provider works with any one of these, checked in order:

1. `ANTHROPIC_API_KEY` — a standard Anthropic API key from [console.anthropic.com](https://console.anthropic.com/settings/keys). This is **not** the same thing as a Claude Code OAuth token; the two are not interchangeable.
2. A logged-in Claude Code CLI (`claude login` with a Claude Max subscription). The pipeline shells out to `claude -p` and no API key is needed.
3. `CLAUDE_CODE_OAUTH_TOKEN` — a long-lived token from `claude setup-token`, with the `claude` CLI installed. Useful for CI and headless machines. The token is consumed by the CLI, not sent to the Anthropic API directly.

### Visuals (b roll)

| Provider | Cost | Setup | Notes |
|----------|------|-------|-------|
| **Gemini Imagen** | Free tier available | `GEMINI_API_KEY` | Default image provider. |
| **Fallback frames** | Free | None | Solid-color fallback frames if image generation fails. |

### Upload

| Platform | Status | Auth |
|----------|--------|------|
| **YouTube** | Stable | OAuth (setup wizard) |
| **TikTok** | v3.1 | Coming soon |
| **Instagram Reels** | v3.1 | Coming soon |
| **X (Twitter)** | v3.1 | Coming soon |

## $0.00 Mode (completely free)

Yes, you can run this with zero API spend:

```bash
python -m verticals draft \
  --topic "your topic" \
  --niche tech \
  --provider ollama
```

This creates the script and metadata with a local LLM. Full video production still needs visuals, TTS, captions, and ffmpeg; Edge TTS is free, while Gemini visuals require `GEMINI_API_KEY`.

## Configuration

All keys stored in `~/.verticals/config.json` with 0600 permissions:

| Variable | Required | Used By |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | If using Claude API | Script generation |
| `CLAUDE_CODE_OAUTH_TOKEN` | If using Claude CLI headless | Script generation (via `claude` CLI) |
| `GEMINI_API_KEY` | If using Gemini visuals/LLM | B roll + thumbnails |
| `OPENAI_API_KEY` | If using GPT or an OpenAI-compatible gateway | Script generation |
| `OPENAI_BASE_URL` | Optional | Point the `openai` provider at a compatible gateway, e.g. `https://api.atlascloud.ai/v1` for [Atlas Cloud](https://www.atlascloud.ai/?utm_source=github&utm_medium=link&utm_campaign=youtube-shorts-pipeline) |
| `OPENAI_MODEL` | Optional | Model id for the `openai` provider (default `gpt-4o-mini`) |
| `ELEVENLABS_API_KEY` | If using ElevenLabs | Premium voiceover |
| `MINIMAX_API_KEY` | If using MiniMax | Script generation + voiceover |
| `SIXTYDB_API_KEY` | If using 60db | Voiceover |

Environment variables override config file values.

Note on `GEMINI_API_KEY`: it must be an AI Studio key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey). Vertex AI or service-account credentials fail with `403: Method doesn't allow unregistered callers`. The same 403 appears when the key is simply not set in the environment the pipeline runs in (a common cause inside Docker — pass it with `docker run -e GEMINI_API_KEY=...`).

## Topic Discovery

Discover trending topics from multiple sources, filtered by niche relevance:

```bash
python -m verticals topics --niche tech --limit 20
```

| Source | Method | Auth | Niche Filtering |
|--------|--------|------|-----------------|
| Reddit | `.json` API | None | Subreddit mapping per niche |
| RSS | feedparser | None | Configurable feeds per niche |
| Google Trends | pytrends | None | Geo + category filtering |
| Twitter/X | Public API | Optional | Keyword filtering |
| TikTok | Apify | Optional | Hashtag mapping |
| YouTube Trending | RSS/API | None | Category mapping |
| Hacker News | API | None | Tech/startup default |

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

| Configuration | Cost |
|---------------|------|
| **Premium** (Claude + Gemini + ElevenLabs) | ~$0.11 |
| **Budget** (Gemini + Gemini + Edge TTS) | ~$0.04 |
| **Draft-only local** (Ollama) | $0.00 |
| **Voice-only free path** (Edge TTS) | $0.00 for voice generation |

## Quality Limits

Verticals is built for repeatable short-form production, not for replacing an editor on story-led creative work.

It works best for:

- news explainers
- niche trend breakdowns
- list-style educational Shorts
- fast social experiments where volume matters

It is not ideal for:

- cinematic storytelling
- creator personality pieces
- videos that require taste, live footage, or strong art direction
- factual topics where the research source quality is weak

Use `draft --dry-run` or `run --dry-run` when testing a new niche. The most important human checkpoint is the draft: hook, factual claims, and whether the video has a real reason to exist.

## Distribution Loop

The pipeline is only the production layer. The useful operating loop is:

- Pick a niche with existing short-form demand.
- Generate and review a small batch of Shorts.
- Publish consistently on the platforms where that niche already moves.
- Use one clear call to action: free resource, newsletter, waitlist, or product.
- Read performance weekly, then tighten the niche profile and hooks.

This repo lowers the cost of testing. It does not remove the need for niche selection, distribution taste, or a real conversion path.

## Project Structure

```
verticals/
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
├── tests/
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
pip install -e ".[dev]"
python -m pytest tests/ -q
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
  Niche intelligence, multi provider LLM support, Edge TTS default, topic discovery, resumable stages, YouTube upload

**v3.1** (planned)
  TikTok/Instagram/X upload, multi language niche profiles, A/B script variants (generate 2, pick better), scheduled batch production

**v3.2** (planned)
  Analytics integration (which Shorts performed best), niche profile auto tuning based on performance data, series support (multi episode narrative arcs)

**Later**
  Web UI, Docker, Google Colab, additional visual providers, stock footage fallback

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
| [**Global Esports**](https://globalesports.in) | South Asia's VCT Pacific franchise — where the esports niche profile was battle-tested |

---

## License

MIT
