from __future__ import annotations
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class EnhanceResponse(BaseModel):
    success: bool
    filename: str
    message: str

class AudioEnhancementJob(BaseModel):

    job_id: str

    input_bucket: str

    input_object_key: str

    output_bucket: str

    output_object_key: str

    noise_reduction: bool = True

    dereverberation: bool = False

    gain_normalization: bool = True

    sample_rate: int = Field(
        default=0,
        ge=0,
    )

    channels: int = Field(
        default=0,
        ge=0,
    )

    output_format: str = "wav"

    bitrate: int = Field(
        default=0,
        ge=0,
    )

    metadata: dict[str, str] = Field(
        default_factory=dict,
    )