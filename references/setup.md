# Setup Guide

This guide covers a fresh install of the YouTube Shorts Pipeline on any machine.  
**First run of `pipeline.py` triggers the setup wizard automatically** — this guide is for reference and for anyone who prefers manual setup.

---

## 1. Install Python Dependencies

Use your preferred Python 3.10+ environment (system Python or a virtual environment — your choice).

```bash
pip install anthropic \
            google-api-python-client \
            google-auth \
            google-auth-oauthlib \
            pillow \
            requests
```

**Optional (for Whisper captions):**
```bash
pip install openai-whisper
```

---

## 2. Install System Tools

### macOS (Homebrew)
```bash
brew install ffmpeg
```

### Ubuntu/Debian
```bash
apt install ffmpeg
```

Whisper is installed via pip (above). No separate system package needed.

---

## 3. Get Your API Keys

### Anthropic (Claude) — Required
Used for script generation.
1. Go to https://console.anthropic.com/settings/keys
2. Create a new API key
3. Copy the key — you'll enter it in the setup wizard

### ElevenLabs — Optional
Used for professional voiceover. If omitted, macOS `say` command is used as fallback.
- **Note:** Free tier is blocked on server IPs. Pro plan ($22/mo) required for non-local use.
1. Go to https://elevenlabs.io/settings/api-keys
2. Create a new key and copy it
- Default voice: George (`JBFqnCBsd6RMkjVDRZzb`) — override via `VOICE_ID_EN` env var

### Google Gemini — Required
Used for AI b-roll image generation via Imagen 3.
1. Go to https://aistudio.google.com/apikey
2. Create a new API key and copy it

---

## 4. YouTube OAuth Setup

This gives the pipeline permission to upload to your YouTube channel. You only need to do this once.

### Step 1: Google Cloud Console
1. Go to https://console.cloud.google.com
2. Create a new project (or select an existing one)
3. Go to **APIs & Services → Library**
4. Search for "YouTube Data API v3" and **Enable** it

### Step 2: Create OAuth Credentials
1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth 2.0 Client ID**
3. Application type: **Desktop app**
4. Name it anything (e.g. "YouTube Shorts Pipeline")
5. Click **Create**, then **Download JSON**
6. Save the file as `client_secret.json` somewhere accessible

### Step 3: Run the OAuth Flow
```bash
python3 scripts/setup_youtube_oauth.py
```

This will:
- Ask for the path to your `client_secret.json`
- Open a browser for Google sign-in
- Save the OAuth token to `~/.youtube-shorts-pipeline/youtube_token.json`

Scopes requested: `youtube.upload`, `youtube.force-ssl` (minimum for upload + captions)

---

## 5. Run the Pipeline

### First run — automatic setup wizard
```bash
python3 scripts/pipeline.py draft --news "your topic here"
```

On first run (no `~/.youtube-shorts-pipeline/config.json`), the wizard will prompt for all keys and run the YouTube OAuth flow.

### After setup

```bash
# Draft only (generate script + metadata)
python3 scripts/pipeline.py draft --news "your topic here"

# Produce (generate video from draft)
python3 scripts/pipeline.py produce --draft ~/.youtube-shorts-pipeline/drafts/<id>.json

# Upload
python3 scripts/pipeline.py upload --draft ~/.youtube-shorts-pipeline/drafts/<id>.json

# Full pipeline in one command
python3 scripts/pipeline.py run --news "your topic here"
```

---

## 6. Config Reference

Keys are stored in `~/.youtube-shorts-pipeline/config.json`:

```json
{
  "ANTHROPIC_API_KEY": "YOUR_ANTHROPIC_KEY_HERE",
  "ELEVENLABS_API_KEY": "YOUR_ELEVENLABS_KEY_HERE",
  "GEMINI_API_KEY": "YOUR_GEMINI_KEY_HERE"
}
```

> This file is created with `0600` permissions (owner read/write only). It is listed in `.gitignore` and should never be committed to version control.

You can also set any of these as environment variables — they take priority over the config file.

---

## 7. Troubleshooting

See `troubleshooting.md` in this directory for common errors and fixes.
