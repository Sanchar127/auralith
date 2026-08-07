from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SubscriptionDurationCreate(BaseModel):
    name: str
    duration_months: int
    discount_percentage: Decimal = Decimal("0.00")
    is_active: bool = True


class SubscriptionDurationUpdate(BaseModel):
    name: str | None = None
    duration_months: int | None = None
    discount_percentage: Decimal | None = None
    is_active: bool | None = None


class SubscriptionDurationResponse(BaseModel):
    id: UUID

    name: str
    duration_months: int
    discount_percentage: Decimal
    is_active: bool

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )