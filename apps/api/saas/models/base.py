from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _generate_uuid7() -> UUID:
    try:
        from uuid7 import uuid7
        return uuid7()
    except ImportError:
        import uuid
        return uuid.uuid4()  # Fallback if uuid7 not available


class Base(DeclarativeBase):
    pass


class UUIDMixin:
    """UUIDv7 primary key (time-ordered, no B-tree fragmentation)."""
    id: Mapped[UUID] = mapped_column(primary_key=True, default=_generate_uuid7)


class TimestampMixin:
    """created_at + updated_at on all tables."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow,
    )
