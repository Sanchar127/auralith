from __future__ import annotations

import asyncio
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.core.config import settings
from app.core.logger import logger
from app.db.model.audio_job import AudioJob, AudioJobStatus
from app.db.session import AsyncSessionLocal
from app.storage.minio import minio_storage
from app.workers.celery_app import celery


# ============================================================
# CONFIGURATION
# ============================================================

MAX_RETRIES = 3

RETRY_BACKOFF_SECONDS = 10

MAX_RETRY_BACKOFF_SECONDS = 300

DEFAULT_OUTPUT_CONTENT_TYPE = "audio/wav"


# ============================================================
# EXCEPTIONS
# ============================================================


class AudioJobError(Exception):
    """
    Base exception for audio processing failures.
    """


class AudioJobNotFoundError(AudioJobError):
    """
    AudioJob does not exist.
    """


class AudioJobAlreadyCompleted(AudioJobError):
    """
    AudioJob has already completed.
    """


class AudioJobCancelled(AudioJobError):
    """
    AudioJob has been cancelled.
    """


class PermanentAudioError(AudioJobError):
    """
    Error that should not be retried.
    """


class RetryableAudioError(AudioJobError):
    """
    Temporary error that can safely be retried.
    """


# ============================================================
# DATA STRUCTURES
# ============================================================


@dataclass(frozen=True, slots=True)
class AudioJobData:
    """
    Immutable representation of the fields required by
    the worker.

    This prevents the worker from depending on a detached
    SQLAlchemy ORM object after the database session closes.
    """

    id: uuid.UUID
    user_id: uuid.UUID
    conversation_id: uuid.UUID
    input_object_key: str
    output_object_key: str


# ============================================================
# TIME
# ============================================================


def utcnow() -> datetime:
    """
    Return timezone-aware UTC datetime.
    """

    return datetime.now(timezone.utc)


# ============================================================
# JOB LOADING
# ============================================================


async def _load_job(
    job_id: str,
) -> AudioJobData:
    """
    Load the AudioJob and extract only the fields required
    by the worker.

    The ORM object never escapes the database session.
    """

    try:
        audio_job_id = uuid.UUID(job_id)

    except (ValueError, TypeError) as exc:
        raise PermanentAudioError(
            f"Invalid audio job ID: {job_id}"
        ) from exc

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(AudioJob).where(
                AudioJob.id == audio_job_id
            )
        )

        job = result.scalar_one_or_none()

        if job is None:
            raise AudioJobNotFoundError(
                f"AudioJob {job_id} not found"
            )

        if (
            job.status
            == AudioJobStatus.COMPLETED
        ):
            raise AudioJobAlreadyCompleted(
                f"AudioJob {job_id} is already completed"
            )

        if (
            job.status
            == AudioJobStatus.CANCELLED
        ):
            raise AudioJobCancelled(
                f"AudioJob {job_id} is cancelled"
            )

        if not job.input_object_key:
            raise PermanentAudioError(
                f"AudioJob {job_id} has no input object key"
            )

        if not job.output_object_key:
            raise PermanentAudioError(
                f"AudioJob {job_id} has no output object key"
            )

        return AudioJobData(
            id=job.id,
            user_id=job.user_id,
            conversation_id=job.conversation_id,
            input_object_key=job.input_object_key,
            output_object_key=job.output_object_key,
        )


# ============================================================
# JOB STATE TRANSITIONS
# ============================================================


async def _claim_job(
    job_id: str,
) -> bool:
    """
    Atomically claim a job for processing.

    Returns:
        True  -> this worker owns the job
        False -> another worker already owns it / job finished

    This protects against duplicate Celery deliveries.
    """

    audio_job_id = uuid.UUID(job_id)

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(AudioJob).where(
                AudioJob.id == audio_job_id,
                AudioJob.status
                != AudioJobStatus.COMPLETED,
                AudioJob.status
                != AudioJobStatus.CANCELLED,
            )
        )

        job = result.scalar_one_or_none()

        if job is None:
            return False

        # ----------------------------------------------------
        # Already processing
        # ----------------------------------------------------

        if (
            job.status
            == AudioJobStatus.PROCESSING
        ):
            logger.warning(
                "AudioJob is already PROCESSING. "
                "job_id=%s",
                job_id,
            )

            return False

        # ----------------------------------------------------
        # Claim
        # ----------------------------------------------------

        job.status = AudioJobStatus.PROCESSING
        job.started_at = utcnow()
        job.error = None

        await db.commit()

        return True


async def _mark_completed(
    *,
    job_id: str,
    output_object_key: str,
) -> None:
    """
    Mark AudioJob as successfully completed.
    """

    audio_job_id = uuid.UUID(job_id)

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(AudioJob).where(
                AudioJob.id == audio_job_id
            )
        )

        job = result.scalar_one_or_none()

        if job is None:
            logger.error(
                "AudioJob disappeared before completion. "
                "job_id=%s",
                job_id,
            )
            return

        job.status = AudioJobStatus.COMPLETED
        job.output_object_key = output_object_key
        job.completed_at = utcnow()
        job.error = None

        await db.commit()


async def _mark_failed(
    *,
    job_id: str,
    error: str,
) -> None:
    """
    Mark AudioJob as permanently failed.
    """

    audio_job_id = uuid.UUID(job_id)

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(AudioJob).where(
                AudioJob.id == audio_job_id
            )
        )

        job = result.scalar_one_or_none()

        if job is None:
            logger.error(
                "Cannot mark missing AudioJob as FAILED. "
                "job_id=%s",
                job_id,
            )
            return

        job.status = AudioJobStatus.FAILED
        job.error = error
        job.completed_at = utcnow()

        await db.commit()


# ============================================================
# CELERY TASK
# ============================================================


@celery.task(
    bind=True,
    name="enhance_audio",
    max_retries=MAX_RETRIES,
    acks_late=True,
    reject_on_worker_lost=True,
)
def enhance_audio(
    self,
    job_id: str,
) -> dict[str, Any]:
    """
    Celery entry point.

    RabbitMQ contains only the AudioJob ID.

    The actual audio is stored in MinIO.
    """

    task_id = self.request.id

    logger.info(
        "Audio enhancement task received. "
        "job_id=%s task_id=%s retry=%s",
        job_id,
        task_id,
        self.request.retries,
    )

    try:

        return asyncio.run(
            _process_audio_job(
                job_id=job_id,
                task_id=task_id,
            )
        )

    # ========================================================
    # PERMANENT CONDITIONS
    # ========================================================

    except (
        AudioJobNotFoundError,
        AudioJobAlreadyCompleted,
        AudioJobCancelled,
        PermanentAudioError,
    ) as exc:

        logger.warning(
            "Audio job will not be retried. "
            "job_id=%s task_id=%s reason=%s",
            job_id,
            task_id,
            exc,
        )

        return {
            "job_id": job_id,
            "status": "failed",
            "reason": str(exc),
        }

    # ========================================================
    # RETRYABLE CONDITIONS
    # ========================================================

    except RetryableAudioError as exc:

        logger.warning(
            "Retryable audio error. "
            "job_id=%s task_id=%s retry=%s error=%s",
            job_id,
            task_id,
            self.request.retries,
            exc,
        )

        if (
            self.request.retries
            >= MAX_RETRIES
        ):

            logger.error(
                "Maximum retries reached. "
                "job_id=%s",
                job_id,
            )

            asyncio.run(
                _mark_failed(
                    job_id=job_id,
                    error=str(exc),
                )
            )

            raise

        countdown = min(
            RETRY_BACKOFF_SECONDS
            * (2 ** self.request.retries),
            MAX_RETRY_BACKOFF_SECONDS,
        )

        raise self.retry(
            exc=exc,
            countdown=countdown,
        )

    # ========================================================
    # UNKNOWN EXCEPTION
    # ========================================================

    except Exception as exc:

        logger.exception(
            "Unexpected audio processing error. "
            "job_id=%s task_id=%s",
            job_id,
            task_id,
        )

        if (
            self.request.retries
            >= MAX_RETRIES
        ):

            try:
                asyncio.run(
                    _mark_failed(
                        job_id=job_id,
                        error=(
                            "Unexpected processing error: "
                            f"{exc}"
                        ),
                    )
                )

            except Exception:
                logger.exception(
                    "Failed to persist final failure state. "
                    "job_id=%s",
                    job_id,
                )

            raise

        countdown = min(
            RETRY_BACKOFF_SECONDS
            * (2 ** self.request.retries),
            MAX_RETRY_BACKOFF_SECONDS,
        )

        raise self.retry(
            exc=exc,
            countdown=countdown,
        )


# ============================================================
# PROCESSING PIPELINE
# ============================================================


async def _process_audio_job(
    *,
    job_id: str,
    task_id: str,
) -> dict[str, Any]:
    """
    Complete audio enhancement workflow.

    Steps:

        1. Load AudioJob
        2. Claim AudioJob
        3. Create isolated temporary directory
        4. Download source from MinIO
        5. Run DeepFilterNet
        6. Validate output
        7. Upload enhanced audio
        8. Mark COMPLETED
        9. Cleanup temporary files
    """

    # ========================================================
    # 1. LOAD JOB
    # ========================================================

    job = await _load_job(job_id)

    logger.info(
        "AudioJob loaded. "
        "job_id=%s input=%s output=%s",
        job_id,
        job.input_object_key,
        job.output_object_key,
    )

    # ========================================================
    # 2. CLAIM JOB
    # ========================================================

    claimed = await _claim_job(job_id)

    if not claimed:

        logger.info(
            "AudioJob was not claimed. "
            "Likely duplicate delivery or another worker "
            "is processing it. job_id=%s",
            job_id,
        )

        return {
            "job_id": job_id,
            "status": "ignored",
        }

    logger.info(
        "AudioJob claimed for processing. "
        "job_id=%s task_id=%s",
        job_id,
        task_id,
    )

    # ========================================================
    # 3. TEMPORARY WORKSPACE
    # ========================================================

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix=f"audio-{job_id}-"
        )
    )

    input_path = (
        temp_dir / "input_audio"
    )

    output_path = (
        temp_dir / "enhanced_audio.wav"
    )

    try:

        # ====================================================
        # 4. DOWNLOAD INPUT
        # ====================================================

        logger.info(
            "Downloading audio from MinIO. "
            "job_id=%s object=%s",
            job_id,
            job.input_object_key,
        )

        try:

            await minio_storage.download_file(
                object_name=(
                    job.input_object_key
                ),
                destination=str(
                    input_path
                ),
            )

        except Exception as exc:

            logger.exception(
                "MinIO download failed. "
                "job_id=%s",
                job_id,
            )

            raise RetryableAudioError(
                f"Failed to download audio: {exc}"
            ) from exc

        if not input_path.exists():

            raise RetryableAudioError(
                "MinIO download completed but "
                "input file does not exist"
            )

        if input_path.stat().st_size <= 0:

            raise PermanentAudioError(
                "Input audio file is empty"
            )

        logger.info(
            "Audio downloaded successfully. "
            "job_id=%s size=%s",
            job_id,
            input_path.stat().st_size,
        )

        # ====================================================
        # 5. RUN DEEPFILTERNET
        # ====================================================

        logger.info(
            "Starting DeepFilterNet. "
            "job_id=%s",
            job_id,
        )

        try:

            # ------------------------------------------------
            # IMPORTANT:
            #
            # Replace this with your actual DeepFilterNet
            # implementation.
            # ------------------------------------------------

            from app.audio.enhancer import (
                enhance_audio_file,
            )

            await asyncio.to_thread(
                enhance_audio_file,
                str(input_path),
                str(output_path),
            )

        except PermanentAudioError:
            raise

        except Exception as exc:

            logger.exception(
                "DeepFilterNet processing failed. "
                "job_id=%s",
                job_id,
            )

            raise RetryableAudioError(
                f"DeepFilterNet processing failed: {exc}"
            ) from exc

        logger.info(
            "DeepFilterNet processing completed. "
            "job_id=%s",
            job_id,
        )

        # ====================================================
        # 6. VALIDATE OUTPUT
        # ====================================================

        if not output_path.exists():

            raise RetryableAudioError(
                "DeepFilterNet completed but "
                "output file was not created"
            )

        output_size = (
            output_path.stat().st_size
        )

        if output_size <= 0:

            raise RetryableAudioError(
                "DeepFilterNet generated an empty output"
            )

        logger.info(
            "Enhanced audio validated. "
            "job_id=%s size=%s",
            job_id,
            output_size,
        )

        # ====================================================
        # 7. UPLOAD OUTPUT
        # ====================================================

        logger.info(
            "Uploading enhanced audio to MinIO. "
            "job_id=%s object=%s",
            job_id,
            job.output_object_key,
        )

        try:

            await minio_storage.upload_file(
                file_path=str(
                    output_path
                ),
                object_name=(
                    job.output_object_key
                ),
                content_type=(
                    DEFAULT_OUTPUT_CONTENT_TYPE
                ),
            )

        except Exception as exc:

            logger.exception(
                "MinIO upload failed. "
                "job_id=%s",
                job_id,
            )

            raise RetryableAudioError(
                f"Failed to upload enhanced audio: {exc}"
            ) from exc

        logger.info(
            "Enhanced audio uploaded. "
            "job_id=%s object=%s",
            job_id,
            job.output_object_key,
        )

        # ====================================================
        # 8. MARK COMPLETED
        # ====================================================

        await _mark_completed(
            job_id=job_id,
            output_object_key=(
                job.output_object_key
            ),
        )

        logger.info(
            "AudioJob completed successfully. "
            "job_id=%s task_id=%s",
            job_id,
            task_id,
        )

        return {
            "job_id": job_id,
            "status": "completed",
            "input_object_key": (
                job.input_object_key
            ),
            "output_object_key": (
                job.output_object_key
            ),
        }

    except PermanentAudioError as exc:

        logger.error(
            "Permanent audio processing failure. "
            "job_id=%s error=%s",
            job_id,
            exc,
        )

        await _mark_failed(
            job_id=job_id,
            error=str(exc),
        )

        raise

    finally:

        # ====================================================
        # 9. ALWAYS CLEANUP
        # ====================================================

        try:

            shutil.rmtree(
                temp_dir,
                ignore_errors=True,
            )

            logger.debug(
                "Temporary audio workspace removed. "
                "job_id=%s path=%s",
                job_id,
                temp_dir,
            )

        except Exception:

            logger.warning(
                "Failed to cleanup temporary workspace. "
                "job_id=%s path=%s",
                job_id,
                temp_dir,
                exc_info=True,
            )