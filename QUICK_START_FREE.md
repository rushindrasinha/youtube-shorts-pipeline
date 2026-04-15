# Quick Start — Free Stack (5 Minutes)

**You now have a complete $0/video YouTube Shorts factory.** Here's how to generate your first video in 5 minutes.

---

## Step 1: Set API Keys (2 min)

```bash
# Option A: Export to environment (temporary, just this session)
export GOOGLE_GENAI_API_KEY="your-gemini-key"
export YOUTUBE_API_KEY="your-youtube-api-key"

# Option B: Save to config file (persistent)
mkdir -p ~/.verticals
cat > ~/.verticals/config.json << 'EOF'
{
  "GOOGLE_GENAI_API_KEY": "...",
  "YOUTUBE_API_KEY": "..."
}
EOF
chmod 600 ~/.verticals/config.json
```

Get free keys:

- **Gemini**: https://ai.google.dev (free tier available)
- **YouTube API**: https://console.cloud.google.com (free quota)

---

## Step 2: Generate Your First Video (3 min)

```bash
cd /Users/hanester/projects/collabs/youtube-shorts-pipeline

# Test run (generates draft, skips upload)
python -m verticals run \
  --niche reddit_stories \
  --provider gemini \
  --lang en \
  --discover \
  --auto-pick \
  --dry-run
```

**What happens:**

1. Discovers trending Reddit stories from r/AskReddit, r/NoSleep, etc.
2. LLM picks the best story for virality
3. Generates script, b-roll prompts, music mood
4. Saves draft JSON to `~/.verticals/drafts/`

If dry-run works, **remove `--dry-run` flag** to generate + upload the actual video:

```bash
python -m verticals run \
  --niche reddit_stories \
  --provider gemini \
  --lang en \
  --discover \
  --auto-pick
```

---

## Step 3 (Optional): Learn Hooks from Top Creators (1 min)

Analyze a successful Reddit story creator to learn their hooks:

```bash
python -m verticals analyze \
  --channel "https://youtube.com/@MaliciousCompliance" \
  --niche reddit_stories \
  --provider gemini
```

This extracts hook patterns from their top 20 videos and saves them to `niches/reddit_stories.yaml`. Future videos will use these winning hooks automatically.

---

## Step 4 (Optional): Automate Daily

**Cron (simple):**

```bash
chmod +x scripts/run_reddit_stories.sh
# Edit crontab, add: 0 9 * * * cd /path && ./scripts/run_reddit_stories.sh
crontab -e
```

**n8n (advanced):**

```bash
n8n start
# Import scripts/n8n_workflow_reddit_stories.json via web UI
# Set to run every 6 hours
```

---

## Cost: $0

✅ Gemini free tier (500+ videos/day)
✅ Pexels stock footage (unlimited)
✅ Edge TTS (free, natural voice)
✅ Local Whisper (free captions)
✅ YouTube API free quota
✅ n8n self-hosted (free)

**No credit card. No limits. No surprises.**

---

## Next: Customize for Your Niche

Edit `niches/reddit_stories.yaml` to adjust:

- **Hooks** — Add your own winning patterns
- **Subreddits** — Change content source
- **Voice** — Tune pace/energy
- **Music** — Adjust mood
- **Visuals** — Specify visual style

Or create a completely custom niche:

```bash
cp niches/reddit_stories.yaml niches/my_niche.yaml
# Edit my_niche.yaml
python -m verticals run --niche my_niche --discover --auto-pick
```

---

## Troubleshooting

**"No topics found"**
→ Reddit scraper is rate-limited. Wait 5 min or run: `python -m verticals topics --niche reddit_stories`

**"GOOGLE_GENAI_API_KEY not found"**
→ Set env var or config file (Step 1)

**"Video quality looks poor"**
→ Analyze top creators (`step 3`) to learn hooks
→ Increase script quality by using Claude instead of Gemini

---

## You're Done 🎉

You now have:

- ✅ Full video pipeline (script → visuals → voice → upload)
- ✅ Hook intelligence layer (learns from top creators)
- ✅ Reddit content sourcing (unlimited stories)
- ✅ Automation (daily cron or n8n)
- ✅ Zero cost

Next: **Generate 5 test videos** to see results, then **scale to 10/day** if working well.

Full docs: See `FREE_STACK_SETUP.md` for detailed setup & customization.
