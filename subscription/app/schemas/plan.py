from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SubscriptionPlanCreate(BaseModel):
    """
    Create subscription plan.
    """

    name: str

    description: str | None = None

    price: Decimal

    monthly_tokens: int

    context_window: int = 128000

    duration_id: UUID

    is_active: bool = True


class SubscriptionPlanUpdate(BaseModel):
    """
    Update subscription plan.
    All fields optional.
    """

    name: str | None = None

    description: str | None = None

    price: Decimal | None = None

    monthly_tokens: int | None = None

    context_window: int | None = None

    duration_id: UUID | None = None

    is_active: bool | None = None


class SubscriptionPlanResponse(BaseModel):
    """
    Response schema.
    """

    id: UUID

    name: str

    description: str | None

    price: Decimal

    monthly_tokens: int

    context_window: int

    duration_id: UUID

    is_active: bool


    model_config = ConfigDict(
        from_attributes=True,
    )


class SubscriptionDurationResponse(BaseModel):

    id: UUID

    name: str

    duration_months: int

    discount_percentage: Decimal

    is_active: bool


    model_config = ConfigDict(
        from_attributes=True,
    )