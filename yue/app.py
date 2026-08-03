from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from service import yue_service


class GenerateRequest(BaseModel):

    genre: str
    lyrics: str


class GenerateResponse(BaseModel):

    success: bool
    job_id: str

    mix: str

    vocals: str | None = None
    instrumental: str | None = None


app = FastAPI(
    title="Yue Service",
)


@app.get("/health")
def health():

    return {
        "status": "ok",
    }


@app.post(
    "/generate",
    response_model=GenerateResponse,
)
def generate(
    request: GenerateRequest,
):

    result = yue_service.generate(
        genre=request.genre,
        lyrics=request.lyrics,
    )

    return GenerateResponse(
        success=True,
        job_id=result["job_id"],
        mix=result["mix"],
        vocals=result.get("vocals"),
        instrumental=result.get("instrumental"),
    )