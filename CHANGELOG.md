# Changelog

## [2.2.0] — 2026-04-01

Multi-LLM code review findings: correctness, security hardening, architecture improvements.

### Fixed
- **Fix `ZeroDivisionError` in video assembly when frames list is empty.** `assemble_video()` now raises a clear `ValueError` instead of crashing on division by zero.
- **Fix swapped zoom effect formulas.** `zoom_in` was actually zooming out and vice versa in `broll.py` — the ffmpeg zoompan `z` expressions are now correct.
- **Fix JSON parsing crash in `draft.py`.** `json.loads()` now has a try/except with regex-based `{...}` extraction fallback for malformed LLM responses.
- **Fix empty YouTube tags.** `upload.py` no longer sends `[""]` when `youtube_tags` is empty — filters out blank entries.
- **Fix version mismatch.** `__init__.py` now matches `pyproject.toml` at `2.1.0` (was `2.0.0`).
- **Fix `cmd_run` fragile inline classes.** Replaced ad-hoc `ProduceArgs`/`UploadArgs` with standard `argparse.Namespace`.
- **Fix Google Trends score calculation.** Uses `enumerate()` instead of relying on DataFrame index for rank-based scoring.
- **Fix `import math` inside loop body** in `reddit.py` — moved to module level.
- **Fix type annotations** in `upload.py`: `Path = None` → `Path | None = None`.

### Security
- **Mask API key input during setup.** `config.py` now uses `getpass.getpass()` instead of `input()` to suppress terminal echo.
- **Harden `run_cmd` wrapper.** Removed `**kwargs` passthrough to `subprocess.run`, preventing callers from injecting `shell=True`.
- **Prevent flag injection in macOS `say` fallback.** Added `--` separator before script text in `voiceover.py`.
- **Validate RSS feed URL schemes.** `rss.py` now rejects non-HTTP(S) URLs, preventing SSRF via `file://` or metadata endpoints.
- **Validate Reddit subreddit names.** `reddit.py` now checks subreddit names against `^[a-zA-Z0-9_]+$` before URL construction.
- **Strip newlines from ffmpeg concat paths.** Prevents directive injection in concat demuxer files.
- **Restrict draft JSON file permissions.** `state.py` now writes files with `0o600` (owner-only) like `config.json`.
- **Add `retryable` parameter to `@with_retry`.** Allows filtering which exceptions trigger retries vs. immediate propagation (e.g., skip retrying 401s).

### Improved
- **Wire `fail_stage()` into pipeline orchestration.** `cmd_produce` now records stage failures in the draft JSON before re-raising, enabling operators to distinguish "never attempted" from "attempted and failed" on resume.
- **Eliminate double Whisper transcription.** `select_and_prepare_music()` now accepts pre-computed word timestamps from the captions stage, avoiding a redundant 5-15s Whisper run.
- **Rewrite `test_research.py`.** Previously tested `extract_keywords` (wrong module). Now tests the actual `research_topic()` function with mocked DuckDuckGo responses.
- **Fix build backend.** `pyproject.toml` now uses `setuptools.build_meta` instead of private `setuptools.backends._legacy:_Backend`.
- **Add `pytest-cov` to dev dependencies** and `[tool.pytest.ini_options]` configuration.
- **Pin `pytrends` optional dependency** to `>=4.9.0,<5.0`.

## [2.1.0] — 2026-02-27

Security audit fixes ported to v2 modular architecture.

### Security
- **Fix TOCTOU race in credential file writes.** `write_secret_file()` in `pipeline/config.py` now uses `os.open()` with `0o600` mode to atomically create files with correct permissions, eliminating the brief window where credentials were world-readable. Also applied to `scripts/setup_youtube_oauth.py`.
- **Escape ffmpeg concat file paths.** Single quotes in file paths are now properly escaped in `pipeline/assemble.py` for the ffmpeg concat demuxer.
- **Pin all dependency versions.** `pyproject.toml` and `requirements.txt` now use compatible-release bounds (e.g., `anthropic>=0.39.0,<1.0`) to reduce supply-chain risk.

### Fixed
- **Clear error on expired OAuth token without refresh token.** `pipeline/upload.py` now raises a descriptive `RuntimeError` instead of silently attempting to use expired credentials.

### Added
- Security section in `README.md` documenting all hardening measures.
- `CHANGELOG.md` (this file).

## [2.0.0] — 2026-02-27

Major restructure: modular `pipeline/` package with new features.

### Added
- **Burned-in captions** — word-by-word highlight via ASS subtitles (Whisper word timestamps).
- **Background music** — bundled royalty-free tracks with automatic voice-ducking.
- **Topic engine** — discover trending topics from Reddit, RSS, Google Trends, Twitter, TikTok.
- **Thumbnail generation** — Gemini Imagen + Pillow text overlay, auto-uploaded.
- **Resume capability** — pipeline state tracked per stage, re-runs skip completed work.
- **Retry logic** — `@with_retry` exponential backoff on all API calls.
- **Structured logging** — file + console logging, `--verbose` for debug output.
- **Claude Max support** — use Claude CLI as alternative to API key.
- **78 tests** — comprehensive test suite across all modules.
- `pyproject.toml` with proper packaging.

### Security (carried forward from audit)
- Gemini API key sent via `x-goog-api-key` header, not URL query parameter.
- Sanitized API error responses — no credential reflection.
- YouTube OAuth scope narrowed to `youtube.upload` + `youtube.force-ssl`.
- Default upload privacy set to `private`.
- Prompt injection mitigation — snippet truncation (300 chars) + boundary markers.
- LLM output validation — type-checking on all draft fields.
- `.gitignore` covers credential files, `.env`, output directories.

## [1.0.0] — 2026-02-27

Initial release. Single-file pipeline: draft → produce → upload.
