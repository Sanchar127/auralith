from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from celery import Task

from celery_app import celery
from enhance import DeepFilterNetService
from schemas import AudioEnhancementJob
from storage.minio import minio_storage


logger = logging.getLogger(__name__)

deepfilter_service = DeepFilterNetService()


class AudioEnhancementTask(Task):
    autoretry_for = (
        ConnectionError,
        TimeoutError,
    )

    retry_backoff = True
    retry_backoff_max = 60

    retry_kwargs = {
        "max_retries": 3,
    }


@celery.task(
    bind=True,
    base=AudioEnhancementTask,
    name="deepfilternet.enhance_audio",
)
def enhance_audio(
    self: AudioEnhancementTask,
    payload: dict[str, Any],
) -> dict[str, str]:
    """
    Process an audio enhancement job.

    The complete AudioEnhancementJob is passed through
    RabbitMQ/Celery as a JSON-compatible dictionary.

    Workflow:

        Celery
          ↓
        Validate job
          ↓
        Download input from MinIO
          ↓
        Run DeepFilterNet
          ↓
        Verify output
          ↓
        Upload output to MinIO
    """

    # =========================================================
    # VALIDATE JOB
    # =========================================================

    job = AudioEnhancementJob.model_validate(payload)

    logger.info(
        "Audio enhancement started "
        "job_id=%s",
        job.job_id,
    )

    with tempfile.TemporaryDirectory(
        prefix=f"deepfilter-{job.job_id}-",
    ) as temp_dir:

        temp_path = Path(temp_dir)

        # =====================================================
        # BUILD TEMPORARY PATHS
        # =====================================================

        input_extension = _normalize_input_extension(
            job.input_object_key,
        )

        input_path = (
            temp_path
            / f"input.{input_extension}"
        )

        output_path = (
            temp_path
            / f"output.{job.output_format.lower()}"
        )

        logger.info(
            "Temporary paths prepared "
            "job_id=%s input=%s output=%s",
            job.job_id,
            input_path,
            output_path,
        )

        # =====================================================
        # DOWNLOAD INPUT
        # =====================================================

        logger.info(
            "Downloading input audio "
            "job_id=%s bucket=%s object=%s",
            job.job_id,
            job.input_bucket,
            job.input_object_key,
        )

        minio_storage.download_file(
            bucket=job.input_bucket,
            object_name=job.input_object_key,
            destination=str(input_path),
        )

        # =====================================================
        # VERIFY INPUT
        # =====================================================

        _verify_input_file(input_path)

        logger.info(
            "Input audio verified "
            "job_id=%s size=%d",
            job.job_id,
            input_path.stat().st_size,
        )

        # =====================================================
        # ENHANCE AUDIO
        # =====================================================

        logger.info(
            "Running DeepFilterNet "
            "job_id=%s",
            job.job_id,
        )

        deepfilter_service.enhance(
            input_path=str(input_path),
            output_path=str(output_path),
        )

        # =====================================================
        # VERIFY OUTPUT
        # =====================================================

        _verify_output_file(output_path)

        logger.info(
            "Enhanced audio verified "
            "job_id=%s size=%d",
            job.job_id,
            output_path.stat().st_size,
        )

        # =====================================================
        # UPLOAD OUTPUT
        # =====================================================

        content_type = _content_type(
            job.output_format,
        )

        logger.info(
            "Uploading enhanced audio "
            "job_id=%s bucket=%s object=%s",
            job.job_id,
            job.output_bucket,
            job.output_object_key,
        )

        minio_storage.upload_file(
            bucket=job.output_bucket,
            object_name=job.output_object_key,
            file_path=str(output_path),
            content_type=content_type,
        )

    # =========================================================
    # COMPLETED
    # =========================================================

    logger.info(
        "Audio enhancement completed "
        "job_id=%s output=%s",
        job.job_id,
        job.output_object_key,
    )

    return {
        "job_id": job.job_id,
        "status": "completed",
        "output_object_key": job.output_object_key,
    }


def _verify_input_file(
    input_path: Path,
) -> None:
    """Verify that the downloaded input audio is valid."""

    if not input_path.exists():
        raise RuntimeError(
            "Input audio was not downloaded",
        )

    if not input_path.is_file():
        raise RuntimeError(
            "Downloaded input audio is not a file",
        )

    if input_path.stat().st_size == 0:
        raise RuntimeError(
            "Input audio is empty",
        )


def _verify_output_file(
    output_path: Path,
) -> None:
    """Verify that DeepFilterNet produced a valid output."""

    if not output_path.exists():
        raise RuntimeError(
            "DeepFilterNet did not produce an output file",
        )

    if not output_path.is_file():
        raise RuntimeError(
            "DeepFilterNet output is not a file",
        )

    if output_path.stat().st_size == 0:
        raise RuntimeError(
            "DeepFilterNet produced an empty output file",
        )


def _normalize_input_extension(
    object_key: str,
) -> str:
    """Extract a normalized extension from a MinIO object key."""

    suffix = Path(object_key).suffix.lower()

    if suffix:
        return suffix.lstrip(".")

    return "audio"


def _content_type(
    output_format: str,
) -> str:
    """Return the MIME type for an audio format."""

    content_types = {
        "wav": "audio/wav",
        "mp3": "audio/mpeg",
        "flac": "audio/flac",
        "ogg": "audio/ogg",
    }

    return content_types.get(
        output_format.lower(),
        "application/octet-stream",
    )