from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PlanResponse(BaseModel):
    id: UUID
    name: str
    display_name: str
    price_cents: int
    videos_per_month: int
    channels_limit: int
    team_seats: int
    features: dict
    overage_cents: int

    model_config = {"from_attributes": True}


class SubscriptionResponse(BaseModel):
    plan: PlanResponse
    status: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False

    model_config = {"from_attributes": True}


class PlansListResponse(BaseModel):
    plans: list[PlanResponse]


class CheckoutRequest(BaseModel):
    plan: str = Field(..., min_length=1, max_length=50)


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str
