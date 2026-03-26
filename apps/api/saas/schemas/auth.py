from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: Optional[str] = Field(None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    expires_in: int


class SubscriptionInfo(BaseModel):
    plan: str
    status: str
    videos_used: int = 0
    videos_limit: int = 0
    current_period_end: Optional[datetime] = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    default_lang: str
    default_voice_id: Optional[str] = None
    caption_style: str
    music_genre: str
    subscription: Optional[SubscriptionInfo] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateUserRequest(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    default_lang: Optional[str] = Field(None, max_length=5)
    caption_style: Optional[str] = Field(None, max_length=50)
    music_genre: Optional[str] = Field(None, max_length=50)
