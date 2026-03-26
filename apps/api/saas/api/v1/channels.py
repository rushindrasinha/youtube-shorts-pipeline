"""YouTube Channels API endpoints — connect, list, update, disconnect, verify."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ...api.deps import get_current_user, get_db
from ...models.channel import YouTubeChannel
from ...models.user import User
from ...schemas.channel import (
    ChannelConnectRequest,
    ChannelConnectResponse,
    ChannelListResponse,
    ChannelResponse,
    ChannelUpdate,
    ChannelVerifyResponse,
)
from ...schemas.common import ErrorDetail, ErrorResponse
from ...services.channel_service import ChannelService
from ...services.team_service import TeamService
from ...settings import settings

router = APIRouter()


@router.get("/channels")
def list_channels(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all channels the user can access (personal + team channels)."""
    from ...models.team import TeamMember

    # Personal channels
    personal = (
        db.query(YouTubeChannel)
        .filter(
            YouTubeChannel.user_id == user.id,
            YouTubeChannel.is_active == True,  # noqa: E712
        )
        .all()
    )

    # Team channels (from teams user belongs to)
    team_ids = [
        m.team_id
        for m in db.query(TeamMember)
        .filter(TeamMember.user_id == user.id)
        .all()
    ]

    team_channels = []
    if team_ids:
        team_channels = (
            db.query(YouTubeChannel)
            .filter(
                YouTubeChannel.team_id.in_(team_ids),
                YouTubeChannel.is_active == True,  # noqa: E712
                YouTubeChannel.user_id != user.id,  # avoid duplicates
            )
            .all()
        )

    all_channels = personal + team_channels
    return ChannelListResponse(
        items=[ChannelResponse.model_validate(ch) for ch in all_channels]
    )


@router.post("/channels/connect")
def connect_channel(
    body: ChannelConnectRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start YouTube OAuth flow. Returns the authorization URL."""
    # If team_id provided, verify user is admin+ on that team
    if body.team_id:
        team_service = TeamService(db)
        if not team_service.check_permission(user.id, body.team_id, "admin"):
            raise HTTPException(
                status_code=403,
                detail="Admin role required to connect team channels",
            )

    channel_service = ChannelService(db)
    auth_url = channel_service.generate_oauth_url(
        user_id=user.id,
        team_id=body.team_id,
    )
    return ChannelConnectResponse(auth_url=auth_url)


@router.get("/channels/callback")
def channel_oauth_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    """Handle YouTube OAuth callback. Creates the channel record."""
    channel_service = ChannelService(db)
    try:
        channel = channel_service.handle_oauth_callback(code=code, state=state)
    except Exception as e:
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/channels?error=connection_failed&message={str(e)[:100]}"
        )

    # Redirect to frontend channels page on success
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/channels?connected={channel.channel_id}"
    )


@router.patch("/channels/{channel_id}")
def update_channel(
    channel_id: UUID,
    body: ChannelUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update channel settings (default_privacy, auto_upload)."""
    channel = db.query(YouTubeChannel).filter(YouTubeChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Check access
    channel_service = ChannelService(db)
    if not channel_service.can_access_channel(user.id, channel, db):
        raise HTTPException(status_code=403, detail="Not authorized to modify this channel")

    # For team channels, require admin+ to modify settings
    if channel.team_id:
        team_service = TeamService(db)
        if not team_service.check_permission(user.id, channel.team_id, "admin"):
            raise HTTPException(
                status_code=403,
                detail="Admin role required to modify team channel settings",
            )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(channel, field, value)

    db.commit()
    db.refresh(channel)
    return ChannelResponse.model_validate(channel)


@router.delete("/channels/{channel_id}")
def disconnect_channel(
    channel_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disconnect (deactivate) a YouTube channel."""
    channel = db.query(YouTubeChannel).filter(YouTubeChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    # Only the channel owner or team admin can disconnect
    if channel.user_id != user.id:
        if channel.team_id:
            team_service = TeamService(db)
            if not team_service.check_permission(user.id, channel.team_id, "admin"):
                raise HTTPException(
                    status_code=403,
                    detail="Admin role required to disconnect team channels",
                )
        else:
            raise HTTPException(status_code=403, detail="Not your channel")

    channel.is_active = False
    db.commit()
    return {"status": "ok"}


@router.post("/channels/{channel_id}/verify")
def verify_channel(
    channel_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Test that a channel connection works."""
    channel = db.query(YouTubeChannel).filter(YouTubeChannel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel_service = ChannelService(db)
    if not channel_service.can_access_channel(user.id, channel, db):
        raise HTTPException(status_code=403, detail="Not authorized to access this channel")

    is_valid = channel_service.verify_channel(channel)
    return ChannelVerifyResponse(
        is_valid=is_valid,
        channel_title=channel.channel_title if is_valid else None,
        error=None if is_valid else "Channel connection could not be verified",
    )
