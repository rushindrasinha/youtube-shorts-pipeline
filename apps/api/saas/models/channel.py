from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from .job import Job
    from .team import Team
    from .user import User
    from .video import Video


class YouTubeChannel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "youtube_channels"
    __table_args__ = (
        Index("idx_channels_user", "user_id"),
        Index("idx_channels_team", "team_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    team_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )

    channel_id: Mapped[str] = mapped_column(String(100), nullable=False)
    channel_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    channel_thumbnail: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Encrypted OAuth credentials
    access_token_enc: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_version: Mapped[int] = mapped_column(Integer, default=1)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    scopes: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)

    default_privacy: Mapped[str] = mapped_column(String(20), default="private")
    auto_upload: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_upload_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="youtube_channels")
    team: Mapped[Optional["Team"]] = relationship(back_populates="youtube_channels")
    jobs: Mapped[list["Job"]] = relationship(back_populates="channel")
    videos: Mapped[list["Video"]] = relationship(back_populates="channel")
