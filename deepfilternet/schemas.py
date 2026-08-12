from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class EnhanceResponse(BaseModel):
    success: bool
    filename: str
    message: str