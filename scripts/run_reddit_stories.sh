#!/bin/bash
# Run daily: Generate YouTube Shorts from trending Reddit stories
# Usage: ./run_reddit_stories.sh [niche] [language] [provider]
# Cron: 0 9 * * * cd /path/to/youtube-shorts-pipeline && ./scripts/run_reddit_stories.sh reddit_stories en

set -e

NICHE=${1:-reddit_stories}
LANG=${2:-en}
PROVIDER=${3:-gemini}
DRY_RUN=${4:-}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Reddit Stories → YouTube Shorts Pipeline"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Niche:    $NICHE"
echo "Language: $LANG"
echo "Provider: $PROVIDER"
echo "Time:     $(date)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd "$PROJECT_DIR"

# Run full pipeline: discover → draft → produce → upload
if [ "$DRY_RUN" = "dry-run" ]; then
    echo "🔵 DRY RUN MODE — Draft only"
    python -m verticals run \
        --niche "$NICHE" \
        --provider "$PROVIDER" \
        --lang "$LANG" \
        --discover \
        --auto-pick \
        --dry-run
else
    echo "🚀 FULL PIPELINE — Draft → Produce → Upload"
    python -m verticals run \
        --niche "$NICHE" \
        --provider "$PROVIDER" \
        --lang "$LANG" \
        --discover \
        --auto-pick
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ Pipeline complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
