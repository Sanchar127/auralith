from typing import Literal

from pydantic import BaseModel


class TaskStatusResponse(BaseModel):
    """
    Background task status.
    """

    task_id: str

    status: Literal[
        "PENDING",
        "STARTED",
        "SUCCESS",
        "FAILURE",
        "RETRY",
        "REVOKED",
    ]

    result: dict | None = None