from typing import Literal

from pydantic import BaseModel, Field


class AudioGenerationRequest(BaseModel):
    """
    Structured request for AI audio generation.
    """

    title: str = Field(
        ...,
        description="Title of the generated audio.",
    )

    prompt: str = Field(
        ...,
        description="Detailed prompt describing the audio to generate.",
    )

    genre: str = Field(
        ...,
        description="Audio genre or style.",
        examples=["Lo-Fi", "Rock", "Podcast Intro"],
    )

    mood: str = Field(
        ...,
        description="Desired mood.",
        examples=["Relaxing", "Energetic", "Cinematic"],
    )

    language: str = Field(
        default="English",
        description="Language of vocals or narration.",
    )

    vocals: bool = Field(
        default=True,
        description="Whether vocals should be included.",
    )

    duration: int | None = Field(
        default=None,
        ge=1,
        description="Target duration in seconds.",
    )


class AudioAsset(BaseModel):
    """
    Metadata describing an audio file.
    """

    file_id: str = Field(
        ...,
        description="Unique file identifier.",
    )

    filename: str = Field(
        ...,
        description="Original filename.",
    )

    content_type: str = Field(
        ...,
        description="MIME type.",
        examples=["audio/wav"],
    )

    duration: float | None = Field(
        default=None,
        description="Duration in seconds.",
    )

    sample_rate: int | None = Field(
        default=None,
        description="Sample rate in Hz.",
    )

    channels: int | None = Field(
        default=None,
        description="Number of audio channels.",
    )


class AudioProcessingRequest(BaseModel):
    """
    Request for processing an existing audio file.
    """

    file_id: str = Field(
        ...,
        description="Audio file identifier.",
    )

    operation: Literal[
        "enhance",
        "master",
        "encode",
        "analyze",
    ] = Field(
        ...,
        description="Requested processing operation.",
    )

    output_format: Literal[
        "wav",
        "mp3",
        "flac",
        "aac",
        "ogg",
    ] | None = Field(
        default=None,
        description="Desired output format.",
    )


class AudioProcessingResponse(BaseModel):
    """
    Response returned after an audio processing request.
    """

    success: bool

    task_id: str | None = Field(
        default=None,
        description="Background task identifier.",
    )

    status: str | None = Field(
        default=None,
        description="Task status.",
    )

    output_file: str | None = Field(
        default=None,
        description="Processed output filename.",
    )

    download_url: str | None = Field(
        default=None,
        description="Download URL for the processed file.",
    )

    message: str | None = Field(
        default=None,
        description="Additional information.",
    )