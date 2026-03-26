from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class YouTubeInfo(BaseModel):
    video_id: Optional[str] = None
    url: Optional[str] = None
    status: Optional[str] = None
    uploaded_at: Optional[datetime] = None


class VideoResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    script: Optional[str] = None
    language: str = "en"
    video_url: str
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    file_size_bytes: Optional[int] = None
    resolution: str = "1080x1920"
    youtube: Optional[YouTubeInfo] = None
    job_id: UUID
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class VideoListItem(BaseModel):
    id: UUID
    title: str
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    language: str = "en"
    job_id: UUID
    created_at: datetime
    expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PaginatedVideos(BaseModel):
    items: list[VideoListItem]
    next_cursor: Optional[str] = None
    has_more: bool = False


class DownloadResponse(BaseModel):
    download_url: str
    expires_in: int = 3600
