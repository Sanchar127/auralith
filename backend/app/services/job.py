
# app/services/audio/job_service.py

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.model.audio_job import (
    AudioJob,
    AudioJobStatus,
    AudioJobType,
)


class AudioJobService:

    async def create_enhancement_job(
        self,
        *,
        db: AsyncSession,
        user_id: UUID,
        conversation_id: UUID | None,
        input_object_key: str,
    ) -> AudioJob:

        job_id = uuid4()

        output_object_key = (
            f"audio/enhanced/"
            f"{user_id}/"
            f"{job_id}.wav"
        )

        job = AudioJob(
            id=job_id,
            user_id=user_id,
            conversation_id=conversation_id,
            job_type=AudioJobType.ENHANCE,
            status=AudioJobStatus.QUEUED,
            input_object_key=input_object_key,
            output_object_key=output_object_key,
        )

        db.add(job)

        await db.flush()

        return job

