# Troubleshooting

## YouTube Errors

**`uploadLimitExceeded`**
Daily upload cap hit. Separate from API quota. Wait 24h from first upload of the day.

**`quotaExceeded`**
YouTube Data API daily quota (10,000 units). Check console.cloud.google.com → APIs → YouTube Data API v3 → Quotas. Resets midnight Pacific time.

**`invalidCredentials` / `Token expired`**
Re-run `python scripts/setup_youtube_oauth.py` to refresh the OAuth token.

## ElevenLabs Errors

**`401 Unauthorized`**
Wrong API key. Check `ELEVENLABS_API_KEY` in `~/.youtube-shorts-pipeline/config.json` or your environment variables.

**`403 / blocked`**
Free tier blocked on server IPs. Must use Pro account ($22/mo).

**`voice_not_found`**
Voice ID doesn't exist on your account. Use a shared voice or clone your own.

## ffmpeg Errors

**`drawtext` not found / libfreetype error**
Homebrew ffmpeg doesn't include libfreetype. Text overlays via ffmpeg won't work. Use Pillow for text-on-image instead, or CapCut/Premiere for post-production overlays.

**`moov atom not found`**
File is incomplete or corrupted. Re-download or re-generate the video.

## Gemini / Image Generation Errors

**`API key invalid`**
Check `GEMINI_API_KEY` in `~/.youtube-shorts-pipeline/config.json` or your environment variables.

**`RESOURCE_EXHAUSTED`**
Gemini free tier rate limit. Wait 60 seconds and retry.

## Whisper Errors

**Hindi audio → Urdu script output**
Known Whisper behaviour — it confuses Hindi and Urdu. Use Whisper for timestamps only. Write the Devanagari SRT manually using those timestamps + the known script.

**Very slow transcription**
Base model on CPU: ~5-7 min per 8 min of audio. Normal. Use `--model small` for faster (less accurate) or `--model large` for best accuracy (much slower).

## Captions / ASS Subtitles

**No burned-in captions in output video**
Check if ffmpeg has libass: `ffmpeg -filters 2>&1 | grep ass`. If missing, the pipeline generates SRT but can't burn in ASS. Reinstall ffmpeg with libass support.

**Whisper word timestamps empty**
Whisper `word_timestamps=True` requires the Python API (not CLI). Ensure `openai-whisper` is installed: `pip install openai-whisper`.

## Background Music

**No music in output**
The `music/` directory must contain `.mp3` files. Add royalty-free tracks (e.g. from Pixabay) to `music/` in the project root.

## Topic Engine

**`python -m pipeline topics` returns no results**
Check `~/.youtube-shorts-pipeline/config.json` has `topic_sources` configured. Reddit and RSS are enabled by default. Google Trends requires `pytrends`: `pip install pytrends`.

## Thumbnail

**Custom thumbnail not showing on YouTube**
YouTube requires channel phone verification for custom thumbnails. Verify at YouTube Studio > Settings > Channel > Feature eligibility.

## Resume / State

**Pipeline re-runs completed stages**
Use `--force` only when you want to redo everything. Without it, the pipeline reads `_pipeline_state` from the draft JSON and skips completed stages.

## General

**`ModuleNotFoundError`**
Missing dependency. Run `pip install anthropic google-api-python-client google-auth google-auth-oauthlib pillow requests openai-whisper feedparser` in your environment.

**Draft JSON not found**
Drafts are saved to `~/.youtube-shorts-pipeline/drafts/<timestamp>.json`. Check the timestamp from the draft command output.
