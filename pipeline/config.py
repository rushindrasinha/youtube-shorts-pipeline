"""Key resolution, paths, constants, and setup wizard."""

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────
# Skill home directory — all data lives here
# ─────────────────────────────────────────────────────
SKILL_DIR = Path.home() / ".youtube-shorts-pipeline"
DRAFTS_DIR = SKILL_DIR / "drafts"
MEDIA_DIR = SKILL_DIR / "media"
LOGS_DIR = SKILL_DIR / "logs"
CONFIG_FILE = SKILL_DIR / "config.json"

# ─────────────────────────────────────────────────────
# Video constants
# ─────────────────────────────────────────────────────
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

# ─────────────────────────────────────────────────────
# Voice config — override via env or config.json
# ─────────────────────────────────────────────────────
VOICE_ID_EN = os.environ.get("VOICE_ID_EN", "JBFqnCBsd6RMkjVDRZzb")  # George
VOICE_ID_HI = os.environ.get("VOICE_ID_HI", "JBFqnCBsd6RMkjVDRZzb")

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "from", "by", "is", "are", "was", "were", "be", "been", "has", "have",
    "had", "will", "would", "could", "should", "may", "might", "that", "this",
    "these", "those", "it", "its", "new", "ahead", "as", "into", "up", "out",
    "over", "after",
}


# ─────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────
def write_secret_file(path: Path, content: str):
    """Write a file with 0600 permissions (owner read/write only)."""
    path.write_text(content)
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def run_cmd(cmd, check=True, capture=False, **kwargs):
    if capture:
        r = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
        if check and r.returncode != 0:
            raise RuntimeError(r.stderr)
        return r
    subprocess.run(cmd, check=check, **kwargs)


def extract_keywords(text: str) -> str:
    words = [w.strip(".,!?\"'()[]").lower() for w in text.split()]
    return " ".join([w for w in words if w and w not in STOPWORDS and len(w) > 2][:4])


# ─────────────────────────────────────────────────────
# API key resolution — env → config.json
# ─────────────────────────────────────────────────────
def _get_key(name: str) -> str:
    """Resolve an API key: environment variable first, then config.json."""
    val = os.environ.get(name)
    if val:
        return val
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text())
            val = cfg.get(name)
            if val:
                return val
        except Exception:
            pass
    return ""


def get_anthropic_key() -> str:
    return _get_key("ANTHROPIC_API_KEY")


def get_elevenlabs_key() -> str:
    return _get_key("ELEVENLABS_API_KEY")


def get_gemini_key() -> str:
    return _get_key("GEMINI_API_KEY")


def get_youtube_token_path() -> Path:
    token_path = SKILL_DIR / "youtube_token.json"
    if token_path.exists():
        return token_path
    raise FileNotFoundError(
        f"YouTube OAuth token not found at {token_path}.\n"
        "Run: python3 scripts/setup_youtube_oauth.py"
    )


def load_config() -> dict:
    """Load the full config.json, including topic_sources."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except Exception:
            pass
    return {}


def save_config(config: dict):
    """Save config.json with restricted permissions."""
    SKILL_DIR.mkdir(parents=True, exist_ok=True)
    write_secret_file(CONFIG_FILE, json.dumps(config, indent=2))


# ─────────────────────────────────────────────────────
# First-run interactive setup
# ─────────────────────────────────────────────────────
def run_setup():
    """Interactive first-run setup — saves config.json and runs YouTube OAuth."""
    print("\n" + "=" * 60)
    print("  YouTube Shorts Pipeline — First-Run Setup")
    print("=" * 60)
    print("\nThis wizard will configure your API keys and YouTube access.")
    print("Keys are saved to ~/.youtube-shorts-pipeline/config.json\n")

    SKILL_DIR.mkdir(parents=True, exist_ok=True)

    config = {}

    print("1. Anthropic API key (required — used for Claude script generation)")
    print("   Get yours at: https://console.anthropic.com/settings/keys")
    key = input("   ANTHROPIC_API_KEY: ").strip()
    if key:
        config["ANTHROPIC_API_KEY"] = key

    print("\n2. ElevenLabs API key (optional — fallback to macOS 'say' if omitted)")
    print("   Pro account required for server use. https://elevenlabs.io/settings/api-keys")
    key = input("   ELEVENLABS_API_KEY (press Enter to skip): ").strip()
    if key:
        config["ELEVENLABS_API_KEY"] = key

    print("\n3. Google Gemini API key (required — used for AI b-roll image generation)")
    print("   Get yours at: https://aistudio.google.com/apikey")
    key = input("   GEMINI_API_KEY: ").strip()
    if key:
        config["GEMINI_API_KEY"] = key

    save_config(config)
    print(f"\n  Config saved to {CONFIG_FILE}")

    print("\n4. YouTube OAuth setup")
    print("   You'll need a client_secret.json from Google Cloud Console.")
    print("   See references/setup.md for step-by-step instructions.")
    run_oauth = input("\n   Run YouTube OAuth now? (y/N): ").strip().lower()
    if run_oauth == "y":
        oauth_script = Path(__file__).resolve().parent.parent / "scripts" / "setup_youtube_oauth.py"
        if oauth_script.exists():
            subprocess.run([sys.executable, str(oauth_script)])
        else:
            print(f"   OAuth script not found at {oauth_script}")
            print("   Run it manually: python3 scripts/setup_youtube_oauth.py")
    else:
        print("   Skipping — run 'python3 scripts/setup_youtube_oauth.py' before uploading.")

    print("\n  Setup complete! Re-run your pipeline command to continue.\n")
    sys.exit(0)
