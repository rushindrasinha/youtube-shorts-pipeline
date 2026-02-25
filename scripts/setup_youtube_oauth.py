#!/usr/bin/env python3
"""
YouTube OAuth Setup
===================
Run once to authorise YouTube API access. Opens a browser window for
Google sign-in and saves the OAuth token to ~/.youtube-shorts-pipeline/youtube_token.json.

Prerequisites:
  1. Go to https://console.cloud.google.com
  2. Create a project (or use an existing one)
  3. Enable the YouTube Data API v3
  4. Create OAuth 2.0 credentials (Desktop app type)
  5. Download the client_secret.json file

Usage:
  python3 scripts/setup_youtube_oauth.py
"""

import json
import os
import stat
import sys
from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",  # needed for captions; narrower than full youtube scope
]

SKILL_DIR  = Path.home() / ".youtube-shorts-pipeline"
TOKEN_PATH = SKILL_DIR / "youtube_token.json"


def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("❌ Missing dependency. Install it with:")
        print("   pip install google-auth-oauthlib google-api-python-client")
        sys.exit(1)

    SKILL_DIR.mkdir(parents=True, exist_ok=True)

    print("YouTube OAuth Setup")
    print("=" * 50)
    print()
    print("You need a client_secret.json from Google Cloud Console.")
    print("Steps:")
    print("  1. Go to https://console.cloud.google.com")
    print("  2. APIs & Services → Credentials")
    print("  3. Create Credentials → OAuth 2.0 Client ID → Desktop app")
    print("  4. Download the JSON file")
    print()

    client_secrets = input("Path to your client_secret.json: ").strip()
    client_secrets = str(Path(client_secrets).expanduser())

    if not Path(client_secrets).exists():
        print(f"❌ File not found: {client_secrets}")
        sys.exit(1)

    print("\nOpening browser for Google sign-in...")
    flow = InstalledAppFlow.from_client_secrets_file(client_secrets, SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_PATH.write_text(creds.to_json())
    TOKEN_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600: owner read/write only
    print(f"\n✅ Token saved to {TOKEN_PATH}")
    print("\nYou're all set! You can now run the pipeline and upload videos.")


if __name__ == "__main__":
    main()
