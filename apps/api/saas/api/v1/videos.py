"""Videos API endpoints — list, detail, download, delete."""

import base64
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...models.video import Video
from ...models.user import User
from ...schemas.common import ErrorDetail, ErrorResponse
from ...schemas.video import (
    DownloadResponse,
    PaginatedVideos,
    VideoListItem,
    VideoResponse,
    YouTubeInfo,
)
from ...services.storage_service import StorageService
from ..deps import get_current_user, get_db

router = APIRouter()


@router.get("", response_model=PaginatedVideos)
async def list_videos(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the current user's completed videos with cursor pagination."""
    query = (
        db.query(Video)
        .filter(Video.user_id == user.id)
        .order_by(Video.created_at.desc())
    )

    # Cursor-based pagination (cursor is base64-encoded created_at timestamp)
    if cursor:
        try:
            from datetime import datetime, timezone

            decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
            cursor_dt = datetime.fromisoformat(decoded)
            query = query.filter(Video.created_at < cursor_dt)
        except (ValueError, Exception):
            raise HTTPException(status_code=400, detail="Invalid cursor")

    # Fetch limit + 1 to determine has_more
    videos = query.limit(limit + 1).all()
    has_more = len(videos) > limit
    items = videos[:limit]

    next_cursor = None
    if has_more and items:
        last_created = items[-1].created_at.isoformat()
        next_cursor = base64.urlsafe_b64encode(last_created.encode()).decode()

    return PaginatedVideos(
        items=[VideoListItem.model_validate(v) for v in items],
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get video detail with S3 URLs."""
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.user_id == user.id)
        .first()
    )
    if not video:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=ErrorDetail(code="NOT_FOUND", message="Video not found")
            ).model_dump(),
        )

    youtube_info = None
    if video.youtube_video_id:
        youtube_info = YouTubeInfo(
            video_id=video.youtube_video_id,
            url=video.youtube_url,
            status=video.youtube_status,
            uploaded_at=video.uploaded_to_youtube_at,
        )

    return VideoResponse(
        id=video.id,
        title=video.title,
        description=video.description,
        tags=video.tags,
        script=video.script,
        language=video.language,
        video_url=video.video_url,
        thumbnail_url=video.thumbnail_url,
        duration_seconds=float(video.duration_seconds) if video.duration_seconds else None,
        file_size_bytes=video.file_size_bytes,
        resolution=video.resolution,
        youtube=youtube_info,
        job_id=video.job_id,
        created_at=video.created_at,
        expires_at=video.expires_at,
    )


@router.get("/{video_id}/download", response_model=DownloadResponse)
async def download_video(
    video_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a presigned download URL for a video."""
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.user_id == user.id)
        .first()
    )
    if not video:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=ErrorDetail(code="NOT_FOUND", message="Video not found")
            ).model_dump(),
        )

    if not video.video_s3_key:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="NOT_FOUND",
                    message="Video file not available (may have expired)",
                )
            ).model_dump(),
        )

    storage = StorageService()
    download_url = storage.get_presigned_url(video.video_s3_key, expires_in=3600)

    return DownloadResponse(download_url=download_url, expires_in=3600)


@router.delete("/{video_id}", status_code=204)
async def delete_video(
    video_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a video and its S3 files."""
    video = (
        db.query(Video)
        .filter(Video.id == video_id, Video.user_id == user.id)
        .first()
    )
    if not video:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=ErrorDetail(code="NOT_FOUND", message="Video not found")
            ).model_dump(),
        )

    # Delete S3 files
    storage = StorageService()
    if video.video_s3_key:
        try:
            storage.delete_file(video.video_s3_key)
        except Exception:
            pass  # Best effort — file may already be gone
    if video.thumbnail_s3_key:
        try:
            storage.delete_file(video.thumbnail_s3_key)
        except Exception:
            pass
    if video.srt_s3_key:
        try:
            storage.delete_file(video.srt_s3_key)
        except Exception:
            pass

    db.delete(video)
    db.commit()


from pydantic import BaseModel as _BM


class UploadYouTubeRequest(_BM):
    channel_id: str
    privacy: str = "private"


@router.post("/videos/{video_id}/upload-youtube")
def upload_to_yt(video_id: str, body: UploadYouTubeRequest, user=Depends(get_current_user), db: Session = Depends(get_db)):
    from uuid import UUID as _UUID
    video = db.query(Video).filter(Video.id == _UUID(video_id), Video.user_id == user.id).first()
    if not video:
        raise HTTPException(404, "Video not found")
    from ...models.channel import YouTubeChannel
    channel = db.query(YouTubeChannel).filter(YouTubeChannel.id == _UUID(body.channel_id)).first()
    if not channel:
        raise HTTPException(404, "Channel not found")
    return {"status": "upload_queued", "video_id": str(video.id)}
