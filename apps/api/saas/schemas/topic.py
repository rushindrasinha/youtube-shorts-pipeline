"""Trending topic Pydantic schemas."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TrendingTopicResponse(BaseModel):
    title: str
    source: str
    trending_score: float
    summary: Optional[str] = None
    url: Optional[str] = None
    metadata: dict = {}

    model_config = {"from_attributes": True}


class TrendingTopicsListResponse(BaseModel):
    items: list[TrendingTopicResponse]
    cached_at: Optional[datetime] = None
    next_refresh_at: Optional[datetime] = None


class QuickCreateRequest(BaseModel):
    topic_title: str = Field(..., min_length=3, max_length=500)
    channel_id: Optional[UUID] = None
