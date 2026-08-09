from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SubscribeRequest(BaseModel):
    """
    Request body for creating a subscription.

    user_id comes from JWT token.
    """

    price_id: UUID



class SubscriptionUpdate(BaseModel):
    """
    Fields that can be updated on a subscription.
    """

    auto_renew: bool | None = None
    status: str | None = None
    expires_at: datetime | None = None



class SubscriptionResponse(BaseModel):

    id: UUID


    plan_id: UUID

    subscription_price_id: UUID

    status: str

    starts_at: datetime

    expires_at: datetime

    auto_renew: bool


    model_config = ConfigDict(
        from_attributes=True,
    )