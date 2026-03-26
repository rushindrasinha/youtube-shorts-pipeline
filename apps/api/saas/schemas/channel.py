"""YouTube channel Pydantic schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChannelConnectRequest(BaseModel):
    team_id: Optional[UUID] = None


class ChannelConnectResponse(BaseModel):
    auth_url: str


class ChannelUpdate(BaseModel):
    default_privacy: Optional[str] = Field(
        None, pattern=r"^(private|unlisted|public)$"
    )
    auto_upload: Optional[bool] = None


class ChannelResponse(BaseModel):
    id: UUID
    channel_id: str
    channel_title: Optional[str] = None
    channel_thumbnail: Optional[str] = None
    default_privacy: str = "private"
    auto_upload: bool = False
    is_active: bool = True
    last_upload_at: Optional[datetime] = None
    team_id: Optional[UUID] = None
    user_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class ChannelListResponse(BaseModel):
    items: list[ChannelResponse]


class ChannelVerifyResponse(BaseModel):
    is_valid: bool
    channel_title: Optional[str] = None
    error: Optional[str] = None
