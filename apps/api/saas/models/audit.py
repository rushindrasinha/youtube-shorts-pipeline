from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDMixin, _utcnow

if TYPE_CHECKING:
    from .team import Team
    from .user import User


class AuditLog(Base, UUIDMixin):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("idx_audit_user", "user_id", "created_at"),
        Index("idx_audit_team", "team_id", "created_at"),
    )

    user_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    team_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("teams.id"), nullable=True
    )

    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)

    details: Mapped[dict] = mapped_column(type_=JSON, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")
    team: Mapped[Optional["Team"]] = relationship(back_populates="audit_logs")
