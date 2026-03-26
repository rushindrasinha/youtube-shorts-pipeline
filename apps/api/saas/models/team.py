from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin, _utcnow

if TYPE_CHECKING:
    from .audit import AuditLog
    from .channel import YouTubeChannel
    from .job import Job
    from .user import User
    from .video import Video


class Team(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "teams"
    __table_args__ = (
        Index("idx_teams_owner", "owner_id"),
        Index("idx_teams_slug", "slug"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # White-label settings
    brand_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    custom_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    max_members: Mapped[int] = mapped_column(Integer, default=10)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    owner: Mapped["User"] = relationship(
        back_populates="owned_teams", foreign_keys=[owner_id]
    )
    members: Mapped[list["TeamMember"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    invites: Mapped[list["TeamInvite"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
    youtube_channels: Mapped[list["YouTubeChannel"]] = relationship(
        back_populates="team",
    )
    jobs: Mapped[list["Job"]] = relationship(
        back_populates="team",
    )
    videos: Mapped[list["Video"]] = relationship(
        back_populates="team",
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="team",
    )


class TeamMember(Base, UUIDMixin):
    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),
        Index("idx_team_members_team", "team_id"),
        Index("idx_team_members_user", "user_id"),
    )

    team_id: Mapped[UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), default="member")
    invited_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    # Relationships
    team: Mapped["Team"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(
        back_populates="team_memberships", foreign_keys=[user_id]
    )
    invited_by_user: Mapped[Optional["User"]] = relationship(
        foreign_keys=[invited_by]
    )


class TeamInvite(Base, UUIDMixin):
    __tablename__ = "team_invites"
    __table_args__ = (
        Index("idx_invites_token", "token"),
        Index("idx_invites_email", "email"),
    )

    team_id: Mapped[UUID] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="member")
    invited_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    # Relationships
    team: Mapped["Team"] = relationship(back_populates="invites")
    invited_by_user: Mapped["User"] = relationship(
        back_populates="team_invites_sent", foreign_keys=[invited_by]
    )
