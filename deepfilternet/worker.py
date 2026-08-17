from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

from app.audio.enhancer import enhance_audio_file
from app.core.config import settings
from app.core.logger import logger
from app.storage.minio import minio_storage
from app.workers.celery_app import celery


def _input_path(job_id: str) -> Path:
    return (
        Path(settings.TEMP_AUDIO_DIR)
        / f"{job_id}_input"
    )


def _output_path(job_id: str) -> Path:
    return (
        Path(settings.TEMP_AUDIO_DIR)
        / f"{job_id}_output.wav"
    )


def _cleanup(
    *paths: Path,
) -> None:

    for path in paths:

        try:

            if path.exists():
                path.unlink()

        except Exception:

            logger.exception(
                "Failed to remove temporary file. "
                "path=%s",
                path,
            )


async def _process_audio(
    payload: dict[str, Any],
) -> None:

    job_id = payload["job_id"]

    input_bucket = payload["input_bucket"]
    input_object_key = payload["input_object_key"]

    output_bucket = payload["output_bucket"]
    output_object_key = payload["output_object_key"]

    input_path = _input_path(job_id)
    output_path = _output_path(job_id)

    try:

        # =====================================================
        # 1. Download input
        # =====================================================

        logger.info(
            "Downloading audio. "
            "job_id=%s object=%s",
            job_id,
            input_object_key,
        )

        await asyncio.to_thread(
            minio_storage.download_file,
            bucket=input_bucket,
            object_name=input_object_key,
            destination=str(input_path),
        )

        # =====================================================
        # 2. Run DeepFilterNet
        # =====================================================

        logger.info(
            "Starting DeepFilterNet. "
            "job_id=%s",
            job_id,
        )

        await asyncio.to_thread(
            enhance_audio_file,
            str(input_path),
            str(output_path),
        )

        # =====================================================
        # 3. Validate output
        # =====================================================

        if not output_path.exists():

            raise RuntimeError(
                "DeepFilterNet did not produce an output file"
            )

        if output_path.stat().st_size == 0:

            raise RuntimeError(
                "DeepFilterNet produced an empty output file"
            )

        # =====================================================
        # 4. Upload result
        # =====================================================

        logger.info(
            "Uploading enhanced audio. "
            "job_id=%s object=%s",
            job_id,
            output_object_key,
        )

        await asyncio.to_thread(
            minio_storage.upload_file,
            bucket=output_bucket,
            object_name=output_object_key,
            file_path=str(output_path),
            content_type="audio/wav",
        )

        logger.info(
            "Audio enhancement completed. "
            "job_id=%s output=%s",
            job_id,
            output_object_key,
        )

    finally:

        # =====================================================
        # 5. Always cleanup local files
        # =====================================================

        _cleanup(
            input_path,
            output_path,
        )


@celery.task(
    bind=True,
    name="enhance_audio",
    max_retries=settings.MAX_RETRIES,
    acks_late=True,
    reject_on_worker_lost=True,
)
def enhance_audio(
    self,
    payload: dict[str, Any],
) -> dict[str, Any]:

    job_id = payload.get("job_id")

    if not job_id:

        raise ValueError(
            "job_id is required"
        )

    try:

        uuid.UUID(job_id)

    except ValueError as exc:

        raise ValueError(
            f"Invalid job_id: {job_id}"
        ) from exc

    logger.info(
        "DeepFilterNet task started. "
        "job_id=%s task_id=%s retry=%s",
        job_id,
        self.request.id,
        self.request.retries,
    )

    try:

        asyncio.run(
            _process_audio(payload)
        )

    except Exception as exc:

        logger.exception(
            "DeepFilterNet task failed. "
            "job_id=%s task_id=%s",
            job_id,
            self.request.id,
        )

        if (
            self.request.retries
            < settings.MAX_RETRIES
        ):

            countdown = min(
                settings.RETRY_BACKOFF
                * (
                    2
                    ** self.request.retries
                ),
                300,
            )

            logger.warning(
                "Retrying DeepFilterNet task. "
                "job_id=%s retry=%s/%s countdown=%s",
                job_id,
                self.request.retries + 1,
                settings.MAX_RETRIES,
                countdown,
            )

            raise self.retry(
                exc=exc,
                countdown=countdown,
            )

        raise

    return {
        "job_id": job_id,
        "status": "completed",
        "output_object_key": payload[
            "output_object_key"
        ],
    }