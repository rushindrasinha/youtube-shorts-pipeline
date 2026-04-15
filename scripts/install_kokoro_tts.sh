#!/bin/bash
# Install Kokoro TTS (Natural narrator voice for Reddit Stories)
# Replaces Edge TTS with premium sound quality
# Usage: ./scripts/install_kokoro_tts.sh

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎙️  Kokoro TTS Installation (Premium Voice)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check Python
echo "✓ Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found"
    exit 1
fi
echo "  ✓ Python $(python3 --version | grep -oE '[0-9]+\.[0-9]+')"

# Install Kokoro + dependencies
echo ""
echo "📦 Installing Kokoro TTS packages..."
pip install -q kokoro-tts soundfile misaki[en]

# Download voice models
echo ""
echo "📥 Downloading Kokoro voice models..."
python3 << 'EOF'
from kokoro import Kokoro
import sys

try:
    k = Kokoro()
    k.download_voices()
    print("✅ Kokoro voices downloaded successfully")

    # List available speakers
    from kokoro.speaker_map import SPEAKER_MAP
    print("\n📢 Available speakers:")
    print("  Female narrators:")
    print("    • af_heart (female, warm, conversational) — RECOMMENDED")
    print("    • af_nicole (female, bright, energetic)")
    print("    • af_jessica (female, calm, professional)")
    print("\n  Male narrators:")
    print("    • am_echo (male, deep, authoritative) — RECOMMENDED")
    print("    • am_michael (male, warm, friendly)")
    print("    • am_adam (male, neutral, clear)")

except Exception as e:
    print(f"❌ Failed to download voices: {e}")
    sys.exit(1)
EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Kokoro TTS Ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next: Update niches/reddit_stories.yaml with:"
echo ""
echo "  voice:"
echo "    engine: kokoro"
echo "    speaker: af_heart  # or am_echo for male"
echo ""
echo "Then test:"
echo "  python -m verticals draft --news 'test' --niche reddit_stories --voice kokoro"
echo ""
