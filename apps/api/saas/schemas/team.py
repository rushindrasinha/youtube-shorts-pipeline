"""Team-related Pydantic schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TeamCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    brand_color: Optional[str] = Field(
        None, pattern=r"^#[0-9A-Fa-f]{6}$", max_length=7
    )


class TeamUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    brand_color: Optional[str] = Field(
        None, pattern=r"^#[0-9A-Fa-f]{6}$", max_length=7
    )
    logo_url: Optional[str] = Field(None, max_length=500)


class TeamResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    owner_id: UUID
    brand_color: Optional[str] = None
    logo_url: Optional[str] = None
    max_members: int = 10
    members_count: int = 0
    channels_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamMemberResponse(BaseModel):
    id: UUID
    user_id: UUID
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    joined_at: datetime

    model_config = {"from_attributes": True}


class InviteMemberRequest(BaseModel):
    email: str = Field(..., max_length=255)
    role: str = Field("member", pattern=r"^(admin|member|viewer)$")


class InviteResponse(BaseModel):
    invite_id: UUID
    email: str
    role: str
    expires_at: datetime

    model_config = {"from_attributes": True}


class UpdateMemberRoleRequest(BaseModel):
    role: str = Field(..., pattern=r"^(admin|member|viewer)$")


class TeamUsageResponse(BaseModel):
    period: str
    period_start: str
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    total_cost_usd: float = 0.0
    members: list[dict] = []
    channels: list[dict] = []
