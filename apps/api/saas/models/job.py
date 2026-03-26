from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin, _utcnow

if TYPE_CHECKING:
    from .channel import YouTubeChannel
    from .team import Team
    from .user import User
    from .video import Video


class Job(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("idx_jobs_user", "user_id"),
        Index("idx_jobs_team", "team_id"),
        Index("idx_jobs_status", "status"),
        Index("idx_jobs_user_status", "user_id", "status"),
        Index("idx_jobs_created", "created_at"),
        Index(
            "idx_jobs_scheduled", "scheduled_at",
            postgresql_where="scheduled_at IS NOT NULL AND status = 'queued'",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    channel_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("youtube_channels.id", ondelete="SET NULL"), nullable=True
    )

    # Input
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(5), default="en")
    voice_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    caption_style: Mapped[str] = mapped_column(String(50), default="yellow_highlight")
    music_genre: Mapped[str] = mapped_column(String(50), default="auto")
    auto_upload: Mapped[bool] = mapped_column(Boolean, default=False)
    upload_privacy: Mapped[str] = mapped_column(String(20), default="private")

    # State
    status: Mapped[str] = mapped_column(String(30), default="queued")
    current_stage: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Results
    video_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("videos.id", ondelete="SET NULL"), nullable=True
    )

    # Cost tracking
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    used_byok: Mapped[bool] = mapped_column(Boolean, default=False)

    # Pipeline state (preserves the PipelineState from CLI)
    pipeline_state: Mapped[dict] = mapped_column(type_=JSON, default=dict)

    # Draft data (the full Claude-generated draft)
    draft_data: Mapped[dict] = mapped_column(type_=JSON, default=dict)

    # Celery task tracking
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Scheduling
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="jobs")
    team: Mapped[Optional["Team"]] = relationship(back_populates="jobs")
    channel: Mapped[Optional["YouTubeChannel"]] = relationship(back_populates="jobs")
    video: Mapped[Optional["Video"]] = relationship(
        back_populates="job", foreign_keys="Video.job_id", uselist=False
    )
    stages: Mapped[list["JobStage"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobStage(Base, UUIDMixin):
    __tablename__ = "job_stages"
    __table_args__ = (
        UniqueConstraint("job_id", "stage_name", name="uq_job_stages_job_stage"),
        Index("idx_stages_job", "job_id"),
    )

    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    stage_name: Mapped[str] = mapped_column(String(30), nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Artifacts (S3 paths, metadata)
    artifacts: Mapped[dict] = mapped_column(type_=JSON, default=dict)

    # Cost for this specific stage
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)

    # Relationships
    job: Mapped["Job"] = relationship(back_populates="stages")
