from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str = Field(
        default_factory=lambda: uuid4().hex,
        description="Conversation ID",
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="User message",
    )


class ChatResponse(BaseModel):
    success: bool

    type: Literal[
        "chat",
        "song",
    ]

    conversation_id: str | None = None

    task_id: str | None = None

    status: str | None = None

    message: str | None = None