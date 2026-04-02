# CLAUDE.md — YouTube Shorts Pipeline

## Environment
- Use `.venv/bin/python3` — system Python blocks pip install (PEP 668)
- Install: `.venv/bin/pip install -e ".[trends,dev]"`
- ffmpeg and ffprobe required (brew install ffmpeg)
- Montserrat font recommended for captions: `brew install --cask font-montserrat`
- Whisper medium model downloads 1.42GB on first run

## API Keys
- Stored in `~/.youtube-shorts-pipeline/config.json` (0o600 permissions)
- ElevenLabs keys can have per-key quota caps — check key settings if getting 401s with credits remaining
- Gemini image models get deprecated frequently — verify model name if 404: `GET /v1beta/models?key=KEY`
- Current models: `gemini-3.1-flash-image-preview` (images), `eleven_v3` (TTS), `claude-sonnet-4-6` (scripts)

## Testing
- `pytest tests/` — 4 pre-existing failures from missing optional deps (feedparser, PIL) are expected
- Tests that import assemble.py will fail without PIL (transitive import via broll.py) — mock or test the regex/logic directly
- Security tests: `pytest tests/test_security.py` — 39 tests covering permissions, injection, validation
- Syntax check all files: `python3 -c "import ast; [ast.parse(open(f).read()) for f in ['pipeline/X.py']]"`

## Architecture
- CLI entry: `pipeline/__main__.py` → subcommands: draft, produce, upload, run, topics
- Pipeline stages: research → draft → broll → voiceover → captions (Remotion or ASS) → music → assemble (+ overlay composite) → thumbnail → upload
- State machine in draft JSON tracks stage completion — `--force` reruns all stages
- All sensitive files written with 0o600 via `write_secret_file()` / `os.open()`
- LLM prompt uses system/user separation (Anthropic `system=` param) for injection defense

## Code Patterns
- `run_cmd(cmd, check, capture)` — no shell=True, no **kwargs (enforced by signature)
- Retry decorator: `@with_retry(max_retries=N, base_delay=N, retryable=(ExcType,))`
- All external content truncated before use (snippets: 300 chars, errors: 200-500 chars)
- ffmpeg filter escaping: must escape `\ : ' ; [ ] ,` in paths for -vf filters
- duck_filter validated against regex allowlist before ffmpeg interpolation

## Remotion (animated captions)
- Project at `remotion/` — run `cd remotion && npm install` before first use
- Transparent video: MUST use ProRes 4444 (`--codec=prores --prores-profile=4444 --pixel-format=yuva444p10le`). VP9 WebM does NOT produce alpha.
- Caption text: use `whiteSpace: "normal"` not `"pre"` — "pre" prevents wrapping, text goes off-screen
- Render from Python: write props to JSON, call `npx remotion render` with `cwd=remotion_dir`
- Falls back to ASS burn-in if Remotion not installed or render fails
- All animations MUST use `useCurrentFrame()` + `interpolate()` — CSS transitions forbidden

## Voice & Music Settings
- Voice: Jessica (female, `cgSgspJ2msm6clMCkdW9`) — stability 0.30, style 0.45
- Music duck levels: 0.25 during speech, 0.50 in gaps — lower values are inaudible
- Audio post-processing: EQ → compression → reverb → LUFS normalization (-14 LUFS)
- Genre-specific music prompts auto-classified by topic mood (tech/story/hype/dark/uplifting)

## Common Tasks
- Full E2E test: `yt-shorts run --news "topic" --dry-run` (skips produce/upload)
- Generate + produce: `yt-shorts draft --news "topic"` then `yt-shorts produce --draft PATH`
- Topic discovery: `yt-shorts topics --limit 10`
