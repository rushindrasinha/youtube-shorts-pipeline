# Changelog

## [1.1.0] — 2026-02-27

### Security
- **Fix TOCTOU race in credential file writes.** `config.json` and `youtube_token.json` are now created atomically with `0600` permissions using `os.open()`, eliminating the brief window where files were world-readable between `write_text()` and `chmod()`. Applies to `pipeline.py` and `setup_youtube_oauth.py`.
- **Move Gemini API key from URL query parameter to `x-goog-api-key` header.** Prevents the key from leaking into server logs, browser history, or error messages.
- **Sanitize Gemini API error responses.** Error messages are truncated and parsed to avoid reflecting credentials.
- **Narrow YouTube OAuth scope.** Replaced the broad `youtube` scope with `youtube.force-ssl` (minimum needed for upload + captions).
- **Default upload privacy set to `private`.** Videos are no longer uploaded as `public` by default.
- **Add prompt injection mitigation.** Research snippets are truncated to 300 characters each and wrapped in boundary markers (`--- BEGIN/END RESEARCH DATA ---`) to reduce the prompt injection surface.
- **Add LLM output validation.** Draft fields returned by Claude are type-checked; `broll_prompts` is validated as a list of strings.
- **Replace API key prefixes in documentation.** Example keys (`sk-ant-...`, `AIza...`) replaced with `YOUR_*_KEY_HERE` placeholders.
- **Add `.gitignore`.** Covers `config.json`, `youtube_token.json`, `client_secret*.json`, `.env`, draft/media output, and Python artifacts.
- **Add `requirements.txt` with pinned dependency bounds.** Reduces supply-chain risk from unpinned `pip install` commands.
- **Escape ffmpeg concat file paths.** Single quotes in file paths are now properly escaped for the ffmpeg concat demuxer.

### Fixed
- **Clear error on expired OAuth token without refresh token.** Previously failed silently at upload time; now raises a descriptive error directing users to re-run the OAuth setup.
- **Fix stale file paths in documentation.** `troubleshooting.md` and `setup.md` now reference `~/.youtube-shorts-pipeline/` instead of legacy paths.

### Added
- `__version__` constant (`1.1.0`) in `pipeline.py`.
- `CHANGELOG.md` (this file).
- `requirements.txt` with compatible-release version bounds.
- Security section in `README.md`.

## [1.0.0] — 2026-02-27

Initial release. Full pipeline: draft → produce → upload.
