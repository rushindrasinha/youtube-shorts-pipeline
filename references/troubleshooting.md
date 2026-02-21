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
Wrong API key. Check `ELEVENLABS_API_KEY` in openclaw.json.

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
Check `~/.openclaw/credentials/nanobanana.key` — should be plain text API key only.

**`RESOURCE_EXHAUSTED`**
Gemini free tier rate limit. Wait 60 seconds and retry.

## Whisper Errors

**Hindi audio → Urdu script output**
Known Whisper behaviour — it confuses Hindi and Urdu. Use Whisper for timestamps only. Write the Devanagari SRT manually using those timestamps + the known script.

**Very slow transcription**
Base model on CPU: ~5-7 min per 8 min of audio. Normal. Use `--model small` for faster (less accurate) or `--model large` for best accuracy (much slower).

## General

**`ModuleNotFoundError`**
You're using system Python instead of venv. Always use `~/clawd/.venv/bin/python`, never `python3`.

**Draft JSON not found**
Drafts are saved to `~/drafts/<timestamp>.json`. Check the timestamp from the draft command output.
