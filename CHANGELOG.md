# Changelog

## [3.0.1] - 2026-05-21

Credibility and viral-traffic cleanup.

### Added
- Added a physical MIT `LICENSE` file so GitHub detects the repository license.
- Added README sections for quality limits and the distribution loop around the production pipeline.
- Added a README v3.0.1 release note that separates shipped features from roadmap items.

### Changed
- `--topic` is now accepted as the public CLI flag, with `--news` retained as a backwards-compatible alias.
- Help and non-generative commands no longer trigger the first-run setup wizard before showing useful output.
- README examples now match the current CLI and implemented provider surface.
- Removed or demoted README claims for unshipped Gradio, Docker, Colab, TikTok/Reels/X upload, Pexels, Replicate, ComfyUI, and Kokoro TTS support.

### Fixed
- Fixed ASS caption highlight colors by writing BGR byte order correctly.
- Fixed `--help` and `--niches` so they can run before API keys are configured.

## [3.0.0] — 2026-04-02

**Verticals: from esports news tool to general purpose AI content engine.**

This is a ground up rethink of the pipeline. The core flow (research → script → visuals → voice → captions → music → assemble → upload) remains the same, but every stage now reads from a niche profile, supports multiple providers, and works for any content vertical.

### Breaking Changes
- **Renamed from `youtube-shorts-pipeline` to `verticals`.** Module import is now `verticals` instead of `pipeline`.
- **Config directory moved** from `~/.youtube-shorts-pipeline/` to `~/.verticals/`.
- **Draft JSON schema changed.** v2 drafts are not directly compatible. A migration script is included: `python -m verticals migrate --drafts-dir <path>`.
- **CLI commands restructured.** `--topic` is the public topic flag, with `--news` kept as a backwards-compatible alias. New `--niche`, `--provider`, `--voice`, and `--platform` flags added.

### Added: Niche Intelligence
- **15 built in niche profiles** (tech, gaming, finance, fitness, cooking, travel, true_crime, science, politics, entertainment, sports, fashion, education, motivation, comedy) plus a `general` fallback.
- Each niche profile is a YAML file that configures: script tone/pacing/hook patterns/CTA variants, visual style and subject vocabulary, voice pace and energy, caption styling (color, font weight, position), music mood and energy, thumbnail style, and topic discovery sources.
- **Custom niches** supported: drop a YAML in `niches/` and use `--niche your_name`.
- Niche profile shapes every stage of the pipeline. Not just the script, but also the b roll prompts, voice selection hints, caption aesthetics, music mood, and thumbnail strategy.

### Added: Multi Provider Support
- **LLM providers:** Claude (Anthropic), Gemini (Google), GPT (OpenAI), Ollama (local). Select with `--provider`.
- **TTS providers:** Edge TTS (free, **new default**), ElevenLabs (premium), macOS say (fallback). Select with `--voice`.
- **Image provider:** Gemini Imagen for b roll and thumbnails, with fallback frames when generation fails.
- **$0.00 draft mode:** Ollama can generate scripts and metadata without API spend.

### Added: Upgraded Script Intelligence
- **Hook pattern system.** Each niche ships with 5 to 8 hook patterns (contrarian_take, breaking_news, prediction, explainer, comparison, story, statistic_shock, question). The LLM is instructed to pick the most appropriate pattern for the topic.
- **Niche aware tone calibration.** The LLM receives explicit tone, pacing, forbidden phrases, and word count guidance from the niche profile.
- **CTA variants.** Each niche has multiple call to action options. The LLM picks contextually.
- **Improved research gate.** Research now optionally scrapes full article content (first 2000 chars) in addition to search snippets, giving the LLM more factual material to work with.
- **Multi platform metadata.** Draft output now includes YouTube title/description/tags, TikTok caption, Instagram caption, and X post text.

### Added: Edge TTS (Free Default Voice)
- **Edge TTS is now the default** TTS provider. Free, cross platform, 300+ voices across 40+ languages. No API key required.
- Niche profiles include suggested Edge TTS voice IDs per language.
- ElevenLabs remains available as the premium option.

### Added: Multi Platform Export
- **YouTube** upload with full metadata, SRT captions, and thumbnail (existing, now default).
- **Platform flag** `--platform youtube|tiktok|reels|x` prepares metadata and aspect ratios for each target.
- TikTok, Instagram Reels, and X upload integrations planned for v3.1. Metadata generation works now.

### Added: Expanded Language Support
- Languages expanded from `en|hi` to `en|hi|es|pt|de|fr|ja|ko` across all providers that support them.
- Edge TTS provides native voices for all supported languages.
- Whisper handles all languages for caption generation.

### Changed: Project Restructure
- Module renamed from `pipeline` to `verticals`.
- Provider logic split into `verticals/providers/` (llm.py, tts.py, image.py, upload.py).
- Stage logic consolidated in `verticals/stages/`.
- Niche profiles live in `niches/` as YAML files.
- Web UI code in `ui/`.

### Changed: Topic Engine Upgrades
- Topic sources now configurable per niche via the niche profile's `discovery` section.
- Added YouTube Trending and Hacker News as topic sources.
- Niche aware auto pick: Claude/LLM evaluates topics specifically for the configured niche, not generically.

### Improved
- **Thumbnail generation** now uses niche profile for style, text position, and color guidance.
- **Music selection** reads niche profile mood and energy to filter track selection.
- **Caption styling** uses niche profile colors and font preferences in ASS generation.
- **B roll prompts** incorporate niche visual vocabulary and avoid lists.

### Fixed
- DuckDuckGo HTML parser now handles edge cases with malformed snippets.
- Whisper model download no longer blocks the main thread on first run.
- ffmpeg concat path escaping improved for Windows compatibility.

### Security
- All v2.1 security measures carry forward.
- YAML niche profiles parsed with `yaml.safe_load()` (no code execution).
- Ollama provider validates model names against allowlist to prevent injection.

## [2.1.0] — 2026-02-27

Security audit fixes ported to v2 modular architecture.

### Security
- **Fix TOCTOU race in credential file writes.** `write_secret_file()` in `pipeline/config.py` now uses `os.open()` with `0o600` mode to atomically create files with correct permissions.
- **Escape ffmpeg concat file paths.** Single quotes in file paths are now properly escaped.
- **Pin all dependency versions.** Compatible release bounds in `pyproject.toml` and `requirements.txt`.

### Fixed
- Clear error on expired OAuth token without refresh token.

### Added
- Security section in README.
- CHANGELOG.md.

## [2.0.0] — 2026-02-27

Major restructure: modular `pipeline/` package with new features.

### Added
- Burned in captions (word by word highlight via ASS subtitles).
- Background music with automatic voice ducking.
- Topic engine (Reddit, RSS, Google Trends, Twitter, TikTok).
- Thumbnail generation (Gemini Imagen + Pillow text overlay).
- Resume capability (stage tracking).
- Retry logic (exponential backoff).
- Structured logging.
- Claude Max support (CLI alternative to API key).
- 78 tests.

## [1.0.0] — 2026-02-27

Initial release. Single file pipeline: draft → produce → upload.
