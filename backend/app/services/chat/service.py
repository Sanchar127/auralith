from __future__ import annotations

import uuid

from fastapi import HTTPException, UploadFile
from celery.result import AsyncResult

import grpc

from app.core.logger import logger

from app.grpc.subscription_client import (
    SubscriptionClient,
)

from app.schemas.chat import ChatResponse

from app.services.rag.pipeline import (
    rag_pipeline,
)

from app.services.token.token_counter import (
    token_counter,
)

from app.services.token.token_usage import (
    TokenUsage,
)


class ChatService:
    """
    Application service responsible for chat orchestration.

    Responsibilities:
    - Validate chat request
    - Estimate token usage
    - Reserve subscription tokens
    - Execute RAG/LLM pipeline
    - Measure actual token usage
    - Settle token reservation
    - Return chat response

    Token balances are NOT managed here.

    The Subscription service owns:
    - wallet
    - subscription
    - reservations
    - token transactions
    """

    def __init__(
        self,
        subscription_client: SubscriptionClient | None = None,
    ) -> None:

        self.subscription_client = (
            subscription_client
            or SubscriptionClient()
        )

    async def chat(
        self,
        *,
        user_id: str,
        conversation_id: str,
        message: str | None,
        file: UploadFile | None = None,
        token_context: dict | None = None,
    ) -> ChatResponse:

        if not user_id:
            raise HTTPException(
                status_code=400,
                detail="user_id is required",
            )

        if not conversation_id:
            raise HTTPException(
                status_code=400,
                detail="conversation_id is required",
            )

        message = message or ""

        if not message.strip() and file is None:
            raise HTTPException(
                status_code=400,
                detail="Message or file is required",
            )

        request_id = str(
            uuid.uuid4()
        )

        model = "llama3"

        logger.info(
            "Chat request started "
            "user_id=%s conversation_id=%s "
            "request_id=%s",
            user_id,
            conversation_id,
            request_id,
        )

        # ---------------------------------------------------------
        # 1. Estimate input tokens
        # ---------------------------------------------------------

        estimated_input_tokens = (
            token_counter.count(message)
        )

        # ---------------------------------------------------------
        # 2. Reserve tokens
        # ---------------------------------------------------------
        #
        # IMPORTANT:
        #
        # We cannot know the exact output token count
        # before running the model.
        #
        # Therefore reserve input + a configured
        # maximum output allowance.
        #
        # In production this should come from
        # the model configuration.
        #

        max_output_tokens = 4096

        estimated_tokens = (
            estimated_input_tokens
            + max_output_tokens
        )

        try:

            reservation = (
                await self.subscription_client.reserve_tokens(
                    user_id=user_id,
                    estimated_tokens=estimated_tokens,
                    request_id=request_id,
                    model=model,
                )
            )

        except grpc.aio.AioRpcError as exc:

            logger.error(
                "Subscription reservation failed "
                "user_id=%s request_id=%s "
                "code=%s",
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
                detail=(
                    "Unable to verify token balance"
                ),
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

        if not reservation.success:

            logger.info(
                "Token reservation rejected "
                "user_id=%s request_id=%s "
                "message=%s",
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

        reservation_id = (
            reservation.reservation_id
        )

        logger.info(
            "Tokens reserved "
            "user_id=%s request_id=%s "
            "reservation_id=%s "
            "tokens=%s",
            user_id,
            request_id,
            reservation_id,
            reservation.reserved_tokens,
        )

        # ---------------------------------------------------------
        # 3. Run RAG / LLM
        # ---------------------------------------------------------

        try:

            response = await rag_pipeline.run(
                conversation_id=conversation_id,
                message=message,
            )

        except Exception as exc:

            logger.exception(
                "AI generation failed "
                "user_id=%s conversation_id=%s "
                "request_id=%s",
                user_id,
                conversation_id,
                request_id,
            )

            #
            # In production:
            #
            # reservation must be released/refunded
            # if generation fails.
            #
            # You should eventually add:
            #
            # ReleaseReservation(...)
            #
            # to the subscription service.
            #

            raise HTTPException(
                status_code=500,
                detail="AI generation failed",
            ) from exc

        # ---------------------------------------------------------
        # 4. Calculate actual usage
        # ---------------------------------------------------------

        #
        # IMPORTANT:
        #
        # This is an estimate unless rag_pipeline
        # returns provider-level token usage.
        #
        # Ideally:
        #
        # response = {
        #     "text": ...,
        #     "usage": {
        #         "input_tokens": ...,
        #         "output_tokens": ...
        #     }
        # }
        #

        input_tokens = (
            token_counter.count(message)
        )

        output_tokens = (
            token_counter.count(response)
        )

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

        # ---------------------------------------------------------
        # 5. Settle actual usage
        # ---------------------------------------------------------

        try:

            settlement = (
                await self.subscription_client.settle_tokens(
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

            #
            # IMPORTANT:
            #
            # Do NOT pretend the request failed.
            #
            # The LLM request succeeded.
            #
            # The settlement should be retried/reconciled
            # asynchronously.
            #

            raise HTTPException(
                status_code=503,
                detail=(
                    "Response generated but "
                    "token settlement is pending"
                ),
            ) from exc

        # ---------------------------------------------------------
        # 6. Validate settlement
        # ---------------------------------------------------------

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
                detail=(
                    "Token settlement failed"
                ),
            )

        # ---------------------------------------------------------
        # 7. Return response
        # ---------------------------------------------------------

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
            conversation_id=conversation_id,
            message=response,
        )

    async def status(
        self,
        task_id: str,
    ) -> dict:

        if not task_id:
            raise HTTPException(
                status_code=400,
                detail="task_id is required",
            )

        task = AsyncResult(task_id)

        result = (
            task.result
            if task.ready()
            else None
        )

        return {
            "task_id": task.id,
            "status": task.status,
            "result": result,
        }

    async def close(self) -> None:
        """
        Gracefully close external connections.
        """

        await self.subscription_client.close()


chat_service = ChatService()