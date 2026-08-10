
from typing import Literal

from pydantic import BaseModel


class ChatResponse(BaseModel):
    success: bool

    type: Literal[
        "chat",
        "enhance",
        "master",
        "encode",
        "analyze",
    ]

    conversation_id: str | None = None

    task_id: str | None = None

    status: str | None = None

    message: str | None = None

