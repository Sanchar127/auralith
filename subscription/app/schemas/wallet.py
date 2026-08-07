from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WalletCreate(BaseModel):
    user_id: UUID
    initial_tokens: int = 0


class WalletUpdate(BaseModel):
    available_tokens: int | None = None


class WalletResponse(BaseModel):
    id: UUID
    user_id: UUID

    available_tokens: int
    lifetime_used_tokens: int

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )