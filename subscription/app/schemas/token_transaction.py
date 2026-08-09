from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TokenTransactionCreate(BaseModel):


    conversation_id: UUID | None = None

    type: str

    model: str

    input_tokens: int = 0

    output_tokens: int = 0

    total_tokens: int

    balance_before: int

    balance_after: int



class TokenTransactionResponse(BaseModel):

    id: UUID


    type: str

    model: str

    total_tokens: int

    balance_before: int

    balance_after: int

    created_at: datetime


    model_config = ConfigDict(
        from_attributes=True
    )