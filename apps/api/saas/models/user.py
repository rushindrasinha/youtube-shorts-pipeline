from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin, _utcnow

if TYPE_CHECKING:
    from .api_keys import UserProviderKey
    from .audit import AuditLog
    from .channel import YouTubeChannel
    from .job import Job
    from .subscription import Subscription, UsageRecord
    from .team import Team, TeamInvite, TeamMember
    from .video import Video


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_email", "email"),
        Index("idx_users_stripe", "stripe_customer_id"),
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True
    )

    # Preferences
    default_lang: Mapped[str] = mapped_column(String(5), default="en")
    default_voice_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    caption_style: Mapped[str] = mapped_column(String(50), default="yellow_highlight")
    music_genre: Mapped[str] = mapped_column(String(50), default="auto")

    # Relationships
    oauth_connections: Mapped[list["OAuthConnection"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    api_keys: Mapped[list["UserAPIKey"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    provider_keys: Mapped[list["UserProviderKey"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    owned_teams: Mapped[list["Team"]] = relationship(
        back_populates="owner", foreign_keys="Team.owner_id"
    )
    team_memberships: Mapped[list["TeamMember"]] = relationship(
        back_populates="user", foreign_keys="TeamMember.user_id",
        cascade="all, delete-orphan",
    )
    team_invites_sent: Mapped[list["TeamInvite"]] = relationship(
        back_populates="invited_by_user", foreign_keys="TeamInvite.invited_by",
    )
    youtube_channels: Mapped[list["YouTubeChannel"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["Job"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    videos: Mapped[list["Video"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    subscription: Mapped[Optional["Subscription"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    usage_records: Mapped[list["UsageRecord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="user",
    )


class OAuthConnection(Base, UUIDMixin):
    __tablename__ = "oauth_connections"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),
        Index("idx_oauth_user", "user_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="oauth_connections")


class UserAPIKey(Base, UUIDMixin):
    __tablename__ = "user_api_keys"
    __table_args__ = (
        Index("idx_api_keys_user", "user_id"),
        Index("idx_api_keys_prefix", "key_prefix"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(8), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="api_keys")
