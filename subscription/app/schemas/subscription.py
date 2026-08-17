from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# =========================================================
# CREATE SUBSCRIPTION
# =========================================================


class SubscribeRequest(BaseModel):
    """
    Request body for creating a subscription.

    The authenticated user's ID comes from the JWT.
    """

    price_id: UUID


# =========================================================
# UPDATE SUBSCRIPTION
# =========================================================


class SubscriptionUpdate(BaseModel):
    """
    Fields that can be updated on a subscription.

    Only fields that actually exist on UserSubscription
    should be exposed here.
    """

    status: str | None = None
    expires_at: datetime | None = None


# =========================================================
# SUBSCRIPTION RESPONSE
# =========================================================


class SubscriptionResponse(BaseModel):
    """
    API response representing a user subscription.
    """

    id: UUID

    plan_id: UUID

    status: str

    starts_at: datetime

    expires_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )