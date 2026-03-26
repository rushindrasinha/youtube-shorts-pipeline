from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    topic: str = Field(..., min_length=3, max_length=500)
    context: str = Field("", max_length=1000)
    language: str = Field("en", pattern=r"^(en|hi)$")
    voice_id: str = Field("", max_length=100)
    caption_style: str = Field("yellow_highlight", max_length=50)
    music_genre: str = Field("auto", max_length=50)
    channel_id: Optional[UUID] = None
    auto_upload: bool = False
    upload_privacy: str = Field("private", pattern=r"^(private|unlisted|public)$")
    scheduled_at: Optional[datetime] = None


class JobStageResponse(BaseModel):
    name: str
    status: str
    duration_ms: Optional[int] = None


class JobResponse(BaseModel):
    id: UUID
    topic: str
    status: str
    progress_pct: int
    current_stage: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    cost_usd: float = 0

    model_config = {"from_attributes": True}


class JobDetailResponse(JobResponse):
    stages: list[JobStageResponse] = []
    error_message: Optional[str] = None
    draft_data: Optional[dict] = None


class PaginatedJobs(BaseModel):
    items: list[JobResponse]
    next_cursor: Optional[str] = None
    has_more: bool = False
