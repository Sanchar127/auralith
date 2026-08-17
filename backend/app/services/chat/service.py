from __future__ import annotations

import uuid
from uuid import UUID

import grpc
from celery.result import AsyncResult
from fastapi import HTTPException, UploadFile
from sqlalchemy import select

from app.core.config import settings
from app.core.logger import logger
from app.db.model.conversation import Conversation
from app.db.session import AsyncSessionLocal
from app.grpc.subscription_client import SubscriptionClient
from app.schemas.chat import ChatResponse
from app.services.job import AudioJobService
from app.services.rag.pipeline import rag_pipeline
from app.services.token.token_counter import token_counter
from app.services.token.token_usage import TokenUsage
from app.storage.minio import minio_storage
from app.storage.validators import validate_audio_file
from app.workers.celery_app import celery


class ChatService:
    """
    Application service responsible for chat orchestration.

    Responsibilities:
    - Create and validate conversations.
    - Handle audio uploads.
    - Create audio enhancement jobs.
    - Queue DeepFilterNet Celery tasks.
    - Execute RAG / LLM requests.
    - Reserve and settle subscription tokens.
    """

    def __init__(
        self,
        subscription_client: SubscriptionClient | None = None,
    ) -> None:
        self.subscription_client = (
            subscription_client
            or SubscriptionClient()
        )

        self.audio_job_service = AudioJobService()

    # =========================================================
    # CONVERSATION
    # =========================================================

    async def _get_or_create_conversation(
        self,
        *,
        user_id: str,
        conversation_id: UUID | None,
    ) -> UUID:
        """
        Return an existing conversation owned by the user,
        or create a new conversation.
        """

        try:
            user_uuid = UUID(user_id)

        except (ValueError, TypeError) as exc:

            raise HTTPException(
                status_code=400,
                detail="Invalid user ID",
            ) from exc

        async with AsyncSessionLocal() as db:

            # -------------------------------------------------
            # CREATE NEW CONVERSATION
            # -------------------------------------------------

            if conversation_id is None:

                new_conversation_id = uuid.uuid4()

                conversation = Conversation(
                    id=new_conversation_id,
                    user_id=user_uuid,
                )

                db.add(conversation)

                await db.commit()

                logger.info(
                    "Conversation created "
                    "user_id=%s conversation_id=%s",
                    user_id,
                    new_conversation_id,
                )

                return new_conversation_id

            # -------------------------------------------------
            # LOAD EXISTING CONVERSATION
            # -------------------------------------------------

            result = await db.execute(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_uuid,
                )
            )

            conversation = result.scalar_one_or_none()

            if conversation is None:

                logger.warning(
                    "Conversation not found or does not belong "
                    "to user_id=%s conversation_id=%s",
                    user_id,
                    conversation_id,
                )

                raise HTTPException(
                    status_code=404,
                    detail="Conversation not found",
                )

            return conversation.id

    # =========================================================
    # MAIN CHAT
    # =========================================================

    async def chat(
        self,
        *,
        user_id: str,
        conversation_id: UUID | None,
        message: str | None,
        file: UploadFile | None = None,
        token_context: dict | None = None,
    ) -> ChatResponse:
        """
        Main chat entry point.

        Audio flow:

            Upload
               ↓
            MinIO
               ↓
            AudioJob PostgreSQL
               ↓
            Build DeepFilterNet payload
               ↓
            Celery / RabbitMQ
               ↓
            DeepFilterNet
               ↓
            MinIO

        Normal chat flow:

            Message
               ↓
            Reserve tokens
               ↓
            RAG / LLM
               ↓
            Calculate usage
               ↓
            Settle tokens
               ↓
            Response
        """

        # =====================================================
        # 0. VALIDATE REQUEST
        # =====================================================

        if not user_id:

            raise HTTPException(
                status_code=400,
                detail="user_id is required",
            )

        message = message or ""

        if not message.strip() and file is None:

            raise HTTPException(
                status_code=400,
                detail="Message or file is required",
            )

        request_id = str(uuid.uuid4())

        logger.info(
            "Chat request started "
            "user_id=%s conversation_id=%s request_id=%s",
            user_id,
            conversation_id,
            request_id,
        )

        # =====================================================
        # 1. GET OR CREATE CONVERSATION
        # =====================================================

        conversation_id = (
            await self._get_or_create_conversation(
                user_id=user_id,
                conversation_id=conversation_id,
            )
        )

        logger.info(
            "Using conversation "
            "user_id=%s conversation_id=%s request_id=%s",
            user_id,
            conversation_id,
            request_id,
        )

        # =====================================================
        # 2. AUDIO PIPELINE
        # =====================================================

        if file is not None:

            return await self._handle_audio(
                user_id=user_id,
                conversation_id=conversation_id,
                file=file,
                request_id=request_id,
            )

        # =====================================================
        # 3. NORMAL LLM CHAT
        # =====================================================

        return await self._handle_chat(
            user_id=user_id,
            conversation_id=conversation_id,
            message=message,
            request_id=request_id,
        )

    # =========================================================
    # AUDIO
    # =========================================================

    async def _handle_audio(
        self,
        *,
        user_id: str,
        conversation_id: UUID,
        file: UploadFile,
        request_id: str,
    ) -> ChatResponse:
        """
        Handle audio upload and queue DeepFilterNet.

        The complete job payload is sent to Celery so the
        DeepFilterNet service does not need access to the
        Auralith PostgreSQL database.
        """

        # =====================================================
        # VALIDATE AUDIO
        # =====================================================

        await validate_audio_file(file)

        logger.info(
            "Audio validation successful "
            "user_id=%s conversation_id=%s "
            "request_id=%s filename=%s",
            user_id,
            conversation_id,
            request_id,
            file.filename,
        )

        # =====================================================
        # UPLOAD ORIGINAL AUDIO TO MINIO
        # =====================================================

        try:

            file_metadata = (
                await minio_storage.upload_chat_file(
                    file=file,
                    user_id=user_id,
                    conversation_id=str(conversation_id),
                )
            )

        except Exception as exc:

            logger.exception(
                "Failed to upload audio "
                "user_id=%s conversation_id=%s "
                "request_id=%s",
                user_id,
                conversation_id,
                request_id,
            )

            raise HTTPException(
                status_code=503,
                detail="Failed to upload audio",
            ) from exc

        input_object_key = file_metadata["object_name"]

        logger.info(
            "Audio uploaded to MinIO "
            "user_id=%s conversation_id=%s "
            "request_id=%s object=%s",
            user_id,
            conversation_id,
            request_id,
            input_object_key,
        )

        # =====================================================
        # CREATE AUDIO JOB
        # =====================================================

        async with AsyncSessionLocal() as db:

            try:

                job = (
                    await self.audio_job_service
                    .create_enhancement_job(
                        db=db,
                        user_id=user_id,
                        conversation_id=conversation_id,
                        input_object_key=input_object_key,
                    )
                )

                await db.commit()

            except Exception as exc:

                await db.rollback()

                logger.exception(
                    "Failed to create audio job "
                    "user_id=%s conversation_id=%s",
                    user_id,
                    conversation_id,
                )

                raise HTTPException(
                    status_code=500,
                    detail="Failed to create audio job",
                ) from exc

            logger.info(
                "Audio enhancement job created "
                "job_id=%s input=%s output=%s",
                job.id,
                job.input_object_key,
                job.output_object_key,
            )

            # =================================================
            # BUILD DEEPFILTERNET PAYLOAD
            # =================================================

            deepfilter_payload = {
                "job_id": str(job.id),

                "input_bucket": settings.MINIO_BUCKET,
                "input_object_key": job.input_object_key,

                "output_bucket": settings.MINIO_BUCKET,
                "output_object_key": job.output_object_key,

                "noise_reduction": True,
                "dereverberation": False,
                "gain_normalization": True,

                "sample_rate": 0,
                "channels": 0,

                "output_format": "wav",

                "bitrate": 0,

                "metadata": {},
            }

            logger.info(
                "DeepFilterNet payload prepared "
                "job_id=%s input=%s output=%s",
                job.id,
                job.input_object_key,
                job.output_object_key,
            )

            # =================================================
            # QUEUE CELERY TASK
            # =================================================

            try:

                task = celery.send_task(
                    "deepfilternet.enhance_audio",
                    args=[deepfilter_payload],
                    queue="deepfilter",
                )

            except Exception as exc:

                logger.exception(
                    "Failed to queue audio enhancement "
                    "job_id=%s",
                    job.id,
                )

                try:

                    from app.models.audio_job import (
                        AudioJobStatus,
                    )

                    job.status = AudioJobStatus.FAILED

                    job.error = (
                        "Failed to queue Celery task: "
                        f"{exc}"
                    )

                    await db.commit()

                except Exception:

                    await db.rollback()

                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Audio processing service "
                        "temporarily unavailable"
                    ),
                ) from exc

            # =================================================
            # STORE CELERY TASK ID
            # =================================================

            job.celery_task_id = task.id

            await db.commit()

            logger.info(
                "Audio enhancement task queued "
                "job_id=%s celery_task_id=%s",
                job.id,
                task.id,
            )

            # =================================================
            # RETURN
            # =================================================

            return ChatResponse(
                success=True,
                type="enhance",
                conversation_id=str(conversation_id),
                task_id=str(job.id),
                status="queued",
                message="Audio enhancement started",
            )

    # =========================================================
    # NORMAL CHAT
    # =========================================================

    async def _handle_chat(
        self,
        *,
        user_id: str,
        conversation_id: UUID,
        message: str,
        request_id: str,
    ) -> ChatResponse:
        """
        Execute the normal RAG / LLM pipeline.
        """

        model = settings.OLLAMA_MODEL

        # =====================================================
        # ESTIMATE INPUT TOKENS
        # =====================================================

        estimated_input_tokens = (
            token_counter.count(message)
        )

        max_output_tokens = 4096

        estimated_tokens = (
            estimated_input_tokens
            + max_output_tokens
        )

        logger.info(
            "Requesting token reservation "
            "user_id=%s request_id=%s "
            "estimated_tokens=%s model=%s",
            user_id,
            request_id,
            estimated_tokens,
            model,
        )

        # =====================================================
        # RESERVE TOKENS
        # =====================================================

        try:

            reservation = (
                await self.subscription_client
                .reserve_tokens(
                    user_id=user_id,
                    estimated_tokens=estimated_tokens,
                    request_id=request_id,
                    model=model,
                )
            )

        except grpc.aio.AioRpcError as exc:

            logger.error(
                "Subscription reservation failed "
                "user_id=%s request_id=%s code=%s",
                user_id,
                request_id,
                exc.code(),
            )

            if exc.code() == grpc.StatusCode.UNAVAILABLE:

                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Subscription service "
                        "temporarily unavailable"
                    ),
                ) from exc

            raise HTTPException(
                status_code=502,
                detail="Unable to verify token balance",
            ) from exc

        except Exception as exc:

            logger.exception(
                "Unexpected token reservation error "
                "user_id=%s request_id=%s",
                user_id,
                request_id,
            )

            raise HTTPException(
                status_code=503,
                detail="Token service unavailable",
            ) from exc

        # =====================================================
        # VALIDATE RESERVATION
        # =====================================================

        if not reservation.success:

            logger.info(
                "Token reservation rejected "
                "user_id=%s request_id=%s message=%s",
                user_id,
                request_id,
                reservation.message,
            )

            raise HTTPException(
                status_code=402,
                detail=(
                    reservation.message
                    or "Insufficient tokens"
                ),
            )

        reservation_id = reservation.reservation_id

        logger.info(
            "Tokens reserved "
            "user_id=%s request_id=%s "
            "reservation_id=%s tokens=%s",
            user_id,
            request_id,
            reservation_id,
            reservation.reserved_tokens,
        )

        # =====================================================
        # RUN RAG / LLM
        # =====================================================

        try:

            response = await rag_pipeline.run(
                conversation_id=str(conversation_id),
                message=message,
            )

        except Exception as exc:

            logger.exception(
                "AI generation failed "
                "user_id=%s conversation_id=%s "
                "request_id=%s reservation_id=%s",
                user_id,
                conversation_id,
                request_id,
                reservation_id,
            )

            raise HTTPException(
                status_code=500,
                detail="AI generation failed",
            ) from exc

        # =====================================================
        # CALCULATE TOKEN USAGE
        # =====================================================

        input_tokens = token_counter.count(message)

        output_tokens = token_counter.count(response)

        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        logger.info(
            "Token usage calculated "
            "user_id=%s request_id=%s "
            "input=%s output=%s total=%s",
            user_id,
            request_id,
            usage.input_tokens,
            usage.output_tokens,
            usage.total_tokens,
        )

        # =====================================================
        # SETTLE TOKENS
        # =====================================================

        try:

            settlement = (
                await self.subscription_client
                .settle_tokens(
                    user_id=user_id,
                    reservation_id=reservation_id,
                    request_id=request_id,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    total_tokens=usage.total_tokens,
                    model=model,
                )
            )

        except grpc.aio.AioRpcError as exc:

            logger.critical(
                "CRITICAL: token settlement failed "
                "after successful AI generation "
                "user_id=%s request_id=%s "
                "reservation_id=%s code=%s",
                user_id,
                request_id,
                reservation_id,
                exc.code(),
            )

            raise HTTPException(
                status_code=503,
                detail=(
                    "Response generated but "
                    "token settlement is pending"
                ),
            ) from exc

        except Exception as exc:

            logger.critical(
                "CRITICAL: unexpected token settlement error "
                "user_id=%s request_id=%s "
                "reservation_id=%s",
                user_id,
                request_id,
                reservation_id,
                exc_info=True,
            )

            raise HTTPException(
                status_code=503,
                detail=(
                    "Response generated but "
                    "token settlement is pending"
                ),
            ) from exc

        # =====================================================
        # VALIDATE SETTLEMENT
        # =====================================================

        if not settlement.success:

            logger.critical(
                "Token settlement rejected "
                "after successful AI generation "
                "user_id=%s request_id=%s "
                "reservation_id=%s message=%s",
                user_id,
                request_id,
                reservation_id,
                settlement.message,
            )

            raise HTTPException(
                status_code=503,
                detail="Token settlement failed",
            )

        # =====================================================
        # RETURN
        # =====================================================

        logger.info(
            "Chat request completed "
            "user_id=%s conversation_id=%s "
            "request_id=%s charged=%s",
            user_id,
            conversation_id,
            request_id,
            settlement.charged_tokens,
        )

        return ChatResponse(
            success=True,
            type="chat",
            conversation_id=str(conversation_id),
            message=response,
        )

    # =========================================================
    # TASK STATUS
    # =========================================================

    async def status(
        self,
        task_id: str,
        user_id: str | None = None,
    ) -> dict:
        """
        Return Celery task status.

        NOTE:
        Since DeepFilterNet uses task_ignore_result=True,
        AsyncResult.result will normally not contain a result.
        """

        if not task_id:

            raise HTTPException(
                status_code=400,
                detail="task_id is required",
            )

        task = AsyncResult(task_id)

        return {
            "task_id": task.id,
            "status": task.status,
            "result": (
                task.result
                if task.ready()
                else None
            ),
        }

    # =========================================================
    # CLOSE
    # =========================================================

    async def close(self) -> None:
        """
        Gracefully close external connections.
        """

        await self.subscription_client.close()


# =============================================================
# SINGLETON
# =============================================================

chat_service = ChatService()