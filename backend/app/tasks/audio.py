
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.core.logger import logger

from app.db.session import AsyncSessionLocal

from app.db.model.audio_job import (
    AudioJob,
    AudioJobStatus,
)

from app.grpc.deepfilter_client import (
    deepfilter_client,
)

from app.workers.celery_app import celery


@celery.task(
    name="enhance_audio",
)
def enhance_audio(job_id: str):
    """
    Celery task responsible for processing an audio
    enhancement job.

    Flow:

        Celery
          ↓
        Load AudioJob
          ↓
        Mark PROCESSING
          ↓
        Call DeepFilterNet through gRPC
          ↓
        DeepFilterNet downloads input from MinIO
          ↓
        DeepFilterNet enhances audio
          ↓
        DeepFilterNet uploads enhanced audio to MinIO
          ↓
        Update AudioJob
    """

    logger.info(
        "Audio enhancement task started. "
        "job_id=%s",
        job_id,
    )

    return asyncio.run(
        _process_audio_job(job_id)
    )


async def _process_audio_job(
    job_id: str,
):
    async with AsyncSessionLocal() as db:

        # =====================================================
        # 1. Validate job ID
        # =====================================================

        try:

            audio_job_id = uuid.UUID(
                job_id
            )

        except ValueError:

            logger.error(
                "Invalid audio job ID: %s",
                job_id,
            )

            raise ValueError(
                f"Invalid audio job ID: {job_id}"
            )

        # =====================================================
        # 2. Load AudioJob
        # =====================================================

        result = await db.execute(
            select(AudioJob).where(
                AudioJob.id == audio_job_id
            )
        )

        job = (
            result.scalar_one_or_none()
        )

        if job is None:

            logger.error(
                "Audio job not found. "
                "job_id=%s",
                job_id,
            )

            raise ValueError(
                f"Audio job {job_id} not found"
            )

        logger.info(
            "Audio job found. "
            "job_id=%s input=%s output=%s",
            job.id,
            job.input_object_key,
            job.output_object_key,
        )

        # =====================================================
        # 3. Mark job as PROCESSING
        # =====================================================

        job.status = (
            AudioJobStatus.PROCESSING
        )

        job.started_at = (
            datetime.now(timezone.utc)
        )

        job.error = None

        await db.commit()

        logger.info(
            "Audio job marked as PROCESSING. "
            "job_id=%s",
            job.id,
        )

        # =====================================================
        # 4. Call DeepFilterNet
        # =====================================================

        try:

            response = (
                await deepfilter_client.enhance_audio(
                    job_id=str(job.id),
                    user_id=str(job.user_id),
                    conversation_id=str(
                        job.conversation_id
                    ),

                    input_bucket=(
                        settings.MINIO_BUCKET
                    ),

                    input_object_key=(
                        job.input_object_key
                    ),

                    output_bucket=(
                        settings.MINIO_BUCKET
                    ),

                    output_object_key=(
                        job.output_object_key
                    ),

                    # -----------------------------------------
                    # Enhancement options
                    # -----------------------------------------

                    noise_reduction=True,

                    dereverberation=False,

                    gain_normalization=True,

                    # 0 = preserve original
                    sample_rate=0,

                    # 0 = preserve original
                    channels=0,

                    output_format="wav",

                    # 0 = service default
                    bitrate=0,

                    metadata={
                        "source": "auralith-backend",
                        "job_type": "audio_enhancement",
                    },
                )
            )

        except Exception as exc:

            logger.exception(
                "DeepFilterNet request failed. "
                "job_id=%s",
                job.id,
            )

            # -----------------------------------------------
            # Mark job as FAILED
            # -----------------------------------------------

            job.status = (
                AudioJobStatus.FAILED
            )

            job.error = str(exc)

            job.completed_at = (
                datetime.now(timezone.utc)
            )

            await db.commit()

            raise

        # =====================================================
        # 5. Check DeepFilter response
        # =====================================================

        logger.info(
            "DeepFilter response received. "
            "job_id=%s status=%s",
            job.id,
            response.status,
        )

        # -----------------------------------------------------
        # DeepFilter FAILED
        # -----------------------------------------------------

        if response.status == (
            response.FAILED
        ):

            error_message = (
                response.error.message
                if response.HasField("error")
                else "DeepFilter enhancement failed"
            )

            logger.error(
                "DeepFilter enhancement failed. "
                "job_id=%s error=%s",
                job.id,
                error_message,
            )

            job.status = (
                AudioJobStatus.FAILED
            )

            job.error = error_message

            job.completed_at = (
                datetime.now(timezone.utc)
            )

            await db.commit()

            raise RuntimeError(
                error_message
            )

        # -----------------------------------------------------
        # DeepFilter cancelled
        # -----------------------------------------------------

        if response.status == (
            response.CANCELLED
        ):

            logger.warning(
                "DeepFilter job cancelled. "
                "job_id=%s",
                job.id,
            )

            job.status = (
                AudioJobStatus.CANCELLED
            )

            job.completed_at = (
                datetime.now(timezone.utc)
            )

            await db.commit()

            return {
                "job_id": str(job.id),
                "status": "cancelled",
            }

        # =====================================================
        # 6. Verify successful output
        # =====================================================

        if response.status != (
            response.COMPLETED
        ):

            logger.warning(
                "DeepFilter returned unexpected "
                "status. job_id=%s status=%s",
                job.id,
                response.status,
            )

            job.status = (
                AudioJobStatus.FAILED
            )

            job.error = (
                "DeepFilter returned unexpected "
                f"status: {response.status}"
            )

            job.completed_at = (
                datetime.now(timezone.utc)
            )

            await db.commit()

            raise RuntimeError(
                job.error
            )

        # -----------------------------------------------------
        # Verify output object
        # -----------------------------------------------------

        if not response.output_object_key:

            logger.error(
                "DeepFilter completed without "
                "output object. job_id=%s",
                job.id,
            )

            job.status = (
                AudioJobStatus.FAILED
            )

            job.error = (
                "DeepFilter completed but "
                "no output object was returned"
            )

            job.completed_at = (
                datetime.now(timezone.utc)
            )

            await db.commit()

            raise RuntimeError(
                job.error
            )

        # =====================================================
        # 7. Mark job as COMPLETED
        # =====================================================

        job.status = (
            AudioJobStatus.COMPLETED
        )

        job.output_object_key = (
            response.output_object_key
        )

        job.completed_at = (
            datetime.now(timezone.utc)
        )

        # -----------------------------------------------------
        # Save processing information if your AudioJob model
        # has these fields.
        # -----------------------------------------------------

        await db.commit()

        logger.info(
            "Audio enhancement completed successfully. "
            "job_id=%s output=%s",
            job.id,
            job.output_object_key,
        )

        # =====================================================
        # 8. Return task result
        # =====================================================

        return {
            "job_id": str(job.id),
            "status": "completed",
            "input_object_key": (
                job.input_object_key
            ),
            "output_object_key": (
                job.output_object_key
            ),
        }

