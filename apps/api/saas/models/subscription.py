from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDMixin, _utcnow

if TYPE_CHECKING:
    from .user import User


class Plan(Base, UUIDMixin):
    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    stripe_price_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Limits
    videos_per_month: Mapped[int] = mapped_column(Integer, nullable=False)
    channels_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    team_seats: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Features (JSON for flexibility)
    features: Mapped[dict] = mapped_column(type_=JSON, default=dict)

    # Pricing
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    overage_cents: Mapped[int] = mapped_column(Integer, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    # Relationships
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="plan",
    )


class Subscription(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("idx_subs_user", "user_id"),
        Index("idx_subs_stripe", "stripe_subscription_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("plans.id"), nullable=False
    )
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, nullable=True
    )

    status: Mapped[str] = mapped_column(String(30), default="active")
    current_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="subscription")
    plan: Mapped["Plan"] = relationship(back_populates="subscriptions")


class UsageRecord(Base, UUIDMixin):
    __tablename__ = "usage_records"
    __table_args__ = (
        UniqueConstraint("user_id", "period_start", name="uq_usage_user_period"),
        Index("idx_usage_user_period", "user_id", "period_start"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    period_start: Mapped[datetime] = mapped_column(Date, nullable=False)
    period_end: Mapped[datetime] = mapped_column(Date, nullable=False)

    videos_created: Mapped[int] = mapped_column(Integer, default=0)
    videos_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    overage_count: Mapped[int] = mapped_column(Integer, default=0)

    # Cost tracking
    total_api_cost: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    total_billed: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)

    stripe_usage_record_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="usage_records")
