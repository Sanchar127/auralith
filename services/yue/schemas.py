from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    genre: str = Field(..., examples=["Pop"])
    lyrics: str = Field(...)


class GenerateResponse(BaseModel):
    success: bool
    job_id: str