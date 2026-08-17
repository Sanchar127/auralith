from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path
from typing import Any

from celery import Task

from celery_app import celery
from enhance import (
    DeepFilterNetExecutionError,
    DeepFilterNetOutputError,
    DeepFilterNetService,
    DeepFilterNetTimeoutError,
)
from schemas import AudioEnhancementJob
from storage.minio import minio_storage


logger = logging.getLogger(__name__)

deepfilter_service = DeepFilterNetService(
    timeout_seconds=600,
)


class AudioEnhancementTask(Task):
    """
    Celery task configuration for audio enhancement.

    Only transient infrastructure failures should be retried
    automatically.

    A malformed job or invalid audio should NOT be retried.
    """

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
) -> dict[str, Any]:
    """
    Enhance an audio file from MinIO using DeepFilterNet.

    Workflow:

        RabbitMQ
            ↓
        Celery
            ↓
        Validate payload
            ↓
        Download from MinIO
            ↓
        Validate local input
            ↓
        DeepFilterNet inference
            ↓
        Validate enhanced audio
            ↓
        Upload enhanced audio to MinIO
            ↓
        Return output metadata
    """

    started_at = time.monotonic()

    # =========================================================
    # 1. VALIDATE JOB
    # =========================================================

    job = AudioEnhancementJob.model_validate(payload)

    logger.info(
        "Audio enhancement started "
        "job_id=%s input=%s output=%s",
        job.job_id,
        job.input_object_key,
        job.output_object_key,
    )

    # =========================================================
    # 2. TEMPORARY WORKSPACE
    # =========================================================

    with tempfile.TemporaryDirectory(
        prefix=f"deepfilter-{job.job_id}-",
    ) as temp_dir:

        temp_path = Path(temp_dir)

        input_extension = _normalize_input_extension(
            job.input_object_key,
        )

        input_path = (
            temp_path
            / f"input.{input_extension}"
        )

        output_extension = (
            job.output_format.lower()
        )

        output_path = (
            temp_path
            / f"enhanced.{output_extension}"
        )

        logger.info(
            "Temporary workspace created "
            "job_id=%s workspace=%s",
            job.job_id,
            temp_path,
        )

        # =====================================================
        # 3. DOWNLOAD FROM MINIO
        # =====================================================

        logger.info(
            "Downloading input "
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
        # 4. VERIFY INPUT
        # =====================================================

        _verify_audio_file(
            input_path,
            name="input",
        )

        input_size = input_path.stat().st_size

        logger.info(
            "Input downloaded "
            "job_id=%s size=%d",
            job.job_id,
            input_size,
        )

        # =====================================================
        # 5. RUN DEEPFILTERNET
        # =====================================================

        logger.info(
            "Starting DeepFilterNet "
            "job_id=%s",
            job.job_id,
        )

        try:

            deepfilter_service.enhance(
                input_path=input_path,
                output_path=output_path,
            )

        except DeepFilterNetTimeoutError:
            logger.exception(
                "DeepFilterNet timed out "
                "job_id=%s",
                job.job_id,
            )
            raise

        except DeepFilterNetExecutionError:
            logger.exception(
                "DeepFilterNet execution failed "
                "job_id=%s",
                job.job_id,
            )
            raise

        except DeepFilterNetOutputError:
            logger.exception(
                "DeepFilterNet output invalid "
                "job_id=%s",
                job.job_id,
            )
            raise

        # =====================================================
        # 6. VERIFY OUTPUT
        # =====================================================

        _verify_audio_file(
            output_path,
            name="enhanced output",
        )

        output_size = output_path.stat().st_size

        logger.info(
            "Enhanced audio verified "
            "job_id=%s size=%d",
            job.job_id,
            output_size,
        )

        # =====================================================
        # 7. UPLOAD TO MINIO
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

        # =====================================================
        # 8. VERIFY REMOTE OBJECT
        # =====================================================

        remote_metadata = (
            minio_storage.stat_object(
                bucket=job.output_bucket,
                object_name=job.output_object_key,
            )
        )

        remote_size = getattr(
            remote_metadata,
            "size",
            None,
        )

        if remote_size is not None:
            if remote_size != output_size:
                raise RuntimeError(
                    "Uploaded output size does not match "
                    "local output size"
                )

        # =====================================================
        # 9. COMPLETE
        # =====================================================

        processing_time = (
            time.monotonic()
            - started_at
        )

        logger.info(
            "Audio enhancement completed "
            "job_id=%s output_bucket=%s "
            "output_object=%s input_size=%d "
            "output_size=%d duration=%.2fs",
            job.job_id,
            job.output_bucket,
            job.output_object_key,
            input_size,
            output_size,
            processing_time,
        )

    # =========================================================
    # 10. RETURN RESULT
    # =========================================================

    return {
        "job_id": job.job_id,
        "status": "completed",

        "output": {
            "bucket": job.output_bucket,
            "object_key": job.output_object_key,
            "content_type": content_type,
            "size": output_size,
        },

        "input": {
            "bucket": job.input_bucket,
            "object_key": job.input_object_key,
            "size": input_size,
        },

        "processing": {
            "duration_seconds": round(
                processing_time,
                3,
            ),
        },
    }


# =============================================================
# HELPERS
# =============================================================

def _verify_audio_file(
    path: Path,
    *,
    name: str,
) -> None:

    if not path.exists():
        raise RuntimeError(
            f"{name} does not exist: {path}"
        )

    if not path.is_file():
        raise RuntimeError(
            f"{name} is not a file: {path}"
        )

    size = path.stat().st_size

    if size <= 0:
        raise RuntimeError(
            f"{name} is empty: {path}"
        )


def _normalize_input_extension(
    object_key: str,
) -> str:

    suffix = Path(object_key).suffix.lower()

    if not suffix:
        return "audio"

    return suffix.lstrip(".")


def _content_type(
    output_format: str,
) -> str:

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