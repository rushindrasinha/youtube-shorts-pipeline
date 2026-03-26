from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDMixin, _utcnow

if TYPE_CHECKING:
    from .channel import YouTubeChannel
    from .job import Job
    from .team import Team
    from .user import User


class Video(Base, UUIDMixin):
    __tablename__ = "videos"
    __table_args__ = (
        Index("idx_videos_user", "user_id"),
        Index("idx_videos_team", "team_id"),
        Index(
            "idx_videos_expires", "expires_at",
            postgresql_where="expires_at IS NOT NULL",
        ),
    )

    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.id"), unique=True, nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("teams.id"), nullable=True
    )
    channel_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("youtube_channels.id"), nullable=True
    )

    # Content
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    script: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(5), default="en")

    # Storage
    video_url: Mapped[str] = mapped_column(String(500), nullable=False)
    video_s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    thumbnail_s3_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    srt_s3_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Metadata
    duration_seconds: Mapped[Optional[float]] = mapped_column(
        Numeric(6, 2), nullable=True
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    resolution: Mapped[str] = mapped_column(String(20), default="1080x1920")

    # YouTube (populated after upload)
    youtube_video_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    youtube_url: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    youtube_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    uploaded_to_youtube_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Expiry (free tier videos expire after 7 days)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    # Relationships
    job: Mapped["Job"] = relationship(back_populates="video", foreign_keys=[job_id])
    user: Mapped["User"] = relationship(back_populates="videos")
    team: Mapped[Optional["Team"]] = relationship(back_populates="videos")
    channel: Mapped[Optional["YouTubeChannel"]] = relationship(
        back_populates="videos"
    )
