from uuid import UUID

from pydantic import BaseModel


class AuthorizeRequest(BaseModel):
    user_id: UUID


class AuthorizeResponse(BaseModel):
    allowed: bool
    active: bool
    remaining_tokens: int
    message: str