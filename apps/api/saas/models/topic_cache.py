from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Index, Numeric, String, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UUIDMixin, _utcnow


class TrendingTopicCache(Base, UUIDMixin):
    __tablename__ = "trending_topics_cache"
    __table_args__ = (
        Index("idx_topics_expires", "expires_at"),
        Index("idx_topics_score", "trending_score"),
    )

    source: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    trending_score: Mapped[Decimal] = mapped_column(Numeric(5, 3), default=0)
    extra_metadata: Mapped[dict] = mapped_column(
        "metadata", type_=JSON, default=dict
    )

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
