"""YouTube channel connection service — OAuth flow, token management."""

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..models.channel import YouTubeChannel
from ..models.user import User
from ..settings import settings
from ..utils.encryption import decrypt_value, encrypt_value

# YouTube OAuth2 configuration
YOUTUBE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
YOUTUBE_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


class ChannelService:
    def __init__(self, db: Session):
        self.db = db

    def generate_oauth_url(self, user_id, team_id=None) -> str:
        """Generate YouTube OAuth URL with state param.

        The state param encodes user_id and optional team_id so the
        callback can associate the channel with the correct owner.
        """
        state_data = json.dumps({"user_id": str(user_id), "team_id": str(team_id) if team_id else None})
        signature = hmac.new(settings.JWT_SECRET_KEY.encode(), state_data.encode(), hashlib.sha256).hexdigest()
        state = f"{state_data}|{signature}"

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": f"{settings.FRONTEND_URL}/api/v1/channels/callback",
            "response_type": "code",
            "scope": " ".join(YOUTUBE_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{YOUTUBE_AUTH_URL}?{query}"

    def handle_oauth_callback(self, code: str, state: str) -> YouTubeChannel:
        """Exchange authorization code for tokens and create channel record.

        In production, this would make HTTP requests to Google's token
        endpoint and YouTube Data API. This implementation provides the
        structure for integration.
        """
        import httpx

        state_data, signature = state.rsplit("|", 1)
        expected = hmac.new(settings.JWT_SECRET_KEY.encode(), state_data.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid OAuth state signature")
        parsed_state = json.loads(state_data)
        user_id = parsed_state["user_id"]
        team_id = parsed_state.get("team_id")

        # Exchange code for tokens
        token_response = httpx.post(
            YOUTUBE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": f"{settings.FRONTEND_URL}/api/v1/channels/callback",
                "grant_type": "authorization_code",
            },
        )
        token_response.raise_for_status()
        tokens = token_response.json()

        access_token = tokens["access_token"]
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 3600)

        # Get channel info from YouTube Data API
        channel_info = httpx.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "snippet", "mine": "true"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        channel_info.raise_for_status()
        channel_data = channel_info.json()

        if not channel_data.get("items"):
            raise ValueError("No YouTube channel found for this account")

        item = channel_data["items"][0]
        channel_id = item["id"]
        channel_title = item["snippet"]["title"]
        channel_thumbnail = item["snippet"]["thumbnails"].get("default", {}).get("url")

        # Encrypt tokens before storing
        channel = YouTubeChannel(
            user_id=user_id,
            team_id=team_id,
            channel_id=channel_id,
            channel_title=channel_title,
            channel_thumbnail=channel_thumbnail,
            access_token_enc=encrypt_value(access_token),
            refresh_token_enc=encrypt_value(refresh_token) if refresh_token else None,
            token_expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
            scopes=YOUTUBE_SCOPES,
            key_version=1,
        )
        self.db.add(channel)
        self.db.commit()
        self.db.refresh(channel)
        return channel

    def refresh_token(self, channel: YouTubeChannel) -> None:
        """Refresh an expired YouTube OAuth token."""
        import httpx

        if not channel.refresh_token_enc:
            raise ValueError("No refresh token available for this channel")

        refresh_tok = decrypt_value(channel.refresh_token_enc)

        response = httpx.post(
            YOUTUBE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_tok,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        tokens = response.json()

        channel.access_token_enc = encrypt_value(tokens["access_token"])
        channel.token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=tokens.get("expires_in", 3600)
        )

        # If a new refresh token was issued, update it
        if tokens.get("refresh_token"):
            channel.refresh_token_enc = encrypt_value(tokens["refresh_token"])

        self.db.commit()

    def verify_channel(self, channel: YouTubeChannel) -> bool:
        """Test that a channel connection works by making a lightweight API call."""
        import httpx

        try:
            access_token = decrypt_value(channel.access_token_enc)

            # Check if token is expired, refresh if needed
            if channel.token_expires_at and channel.token_expires_at < datetime.now(
                timezone.utc
            ):
                self.refresh_token(channel)
                access_token = decrypt_value(channel.access_token_enc)

            response = httpx.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={"part": "id", "mine": "true"},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return response.status_code == 200
        except Exception:
            return False

    def can_access_channel(self, user_id, channel: YouTubeChannel, db: Session) -> bool:
        """Check if a user can access a channel (personal or team member)."""
        # Personal channel
        if channel.user_id == user_id:
            return True

        # Team channel - check membership
        if channel.team_id:
            from ..models.team import TeamMember

            member = (
                db.query(TeamMember)
                .filter(
                    TeamMember.team_id == channel.team_id,
                    TeamMember.user_id == user_id,
                )
                .first()
            )
            return member is not None

        return False
