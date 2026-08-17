from __future__ import annotations

import time

from ollama import AsyncClient

from app.core.config import settings
from app.core.logger import logger
from app.core.metrics import (
    LLM_DURATION_SECONDS,
    LLM_ERRORS_TOTAL,
    LLM_INPUT_TOKENS_TOTAL,
    LLM_OUTPUT_TOKENS_TOTAL,
    LLM_REQUESTS_TOTAL,
)
from app.services.chat.memory import conversation_memory
from app.services.chat.prompt_builder import prompt_builder
from app.services.rag.retriever import rag_retriever
from app.services.token.token_counter import token_counter


class RAGPipeline:
    """
    Complete Retrieval Augmented Generation pipeline.

    Flow:

        User Message
            |
            v
        Conversation Memory
            |
            v
        Qdrant Retriever
            |
            v
        Prompt Builder
            |
            v
        Ollama LLM
            |
            v
        Save Conversation

    Observability:

        LLM request count
        LLM latency
        LLM errors
        LLM input tokens
        LLM output tokens
    """

    SERVICE_NAME = "backend"

    def __init__(self) -> None:
        self.client: AsyncClient | None = None
        self.model = settings.OLLAMA_MODEL

    # ==========================================================
    # LIFECYCLE
    # ==========================================================

    def connect(self) -> None:
        """Create the Ollama client."""

        if self.client is not None:
            return

        self.client = AsyncClient(
            host=settings.OLLAMA_BASE_URL,
        )

        logger.info(
            "Connected to Ollama at %s",
            settings.OLLAMA_BASE_URL,
        )

    async def close(self) -> None:
        """Close the Ollama client."""

        if self.client is None:
            return

        self.client = None

        logger.info(
            "Ollama client closed."
        )

    def _get_client(self) -> AsyncClient:
        """Return the initialized Ollama client."""

        if self.client is None:
            raise RuntimeError(
                "Ollama client is not initialized. "
                "Call connect() first."
            )

        return self.client

    # ==========================================================
    # RAG PIPELINE
    # ==========================================================

    async def run(
        self,
        conversation_id: str,
        message: str,
    ) -> str:
        """
        Execute the complete RAG conversation pipeline.
        """

        logger.info(
            "Starting RAG pipeline."
        )

        client = self._get_client()

        # ======================================================
        # LOAD CONVERSATION HISTORY
        # ======================================================

        history = await conversation_memory.get_messages(
            conversation_id
        )

        logger.debug(
            "Loaded %s previous messages.",
            len(history),
        )

        # ======================================================
        # RETRIEVE KNOWLEDGE FROM QDRANT
        # ======================================================

        context = await rag_retriever.retrieve_context(
            message
        )

        logger.debug(
            "Retrieved context length=%s",
            len(context),
        )

        # ======================================================
        # BUILD OLLAMA MESSAGES
        # ======================================================

        messages = prompt_builder.build(
            message=message,
            context=context,
            history=history,
        )

        logger.debug(
            "Prompt built with %s messages.",
            len(messages),
        )

        # ======================================================
        # LLM REQUEST
        # ======================================================

        start_time = time.perf_counter()

        LLM_REQUESTS_TOTAL.labels(
            service=self.SERVICE_NAME,
            model=self.model,
            status="started",
        ).inc()

        try:

            response = await client.chat(
                model=self.model,
                messages=messages,
            )

            answer = response["message"]["content"]

            duration = (
                time.perf_counter() - start_time
            )

            # --------------------------------------------------
            # LLM LATENCY
            # --------------------------------------------------

            LLM_DURATION_SECONDS.labels(
                service=self.SERVICE_NAME,
                model=self.model,
            ).observe(
                duration
            )

            # --------------------------------------------------
            # TOKEN USAGE
            # --------------------------------------------------

            input_tokens = token_counter.count(
                message
            )

            output_tokens = token_counter.count(
                answer
            )

            LLM_INPUT_TOKENS_TOTAL.labels(
                service=self.SERVICE_NAME,
                model=self.model,
            ).inc(
                input_tokens
            )

            LLM_OUTPUT_TOKENS_TOTAL.labels(
                service=self.SERVICE_NAME,
                model=self.model,
            ).inc(
                output_tokens
            )

            # --------------------------------------------------
            # SUCCESS
            # --------------------------------------------------

            LLM_REQUESTS_TOTAL.labels(
                service=self.SERVICE_NAME,
                model=self.model,
                status="success",
            ).inc()

            logger.info(
                "RAG response generated successfully "
                "model=%s input_tokens=%s "
                "output_tokens=%s duration=%.3fs",
                self.model,
                input_tokens,
                output_tokens,
                duration,
            )

        except Exception as exc:

            duration = (
                time.perf_counter() - start_time
            )

            # --------------------------------------------------
            # LLM LATENCY
            # --------------------------------------------------

            LLM_DURATION_SECONDS.labels(
                service=self.SERVICE_NAME,
                model=self.model,
            ).observe(
                duration
            )

            # --------------------------------------------------
            # LLM ERROR
            # --------------------------------------------------

            LLM_ERRORS_TOTAL.labels(
                service=self.SERVICE_NAME,
                model=self.model,
                error_type="generation",
            ).inc()

            # --------------------------------------------------
            # REQUEST ERROR
            # --------------------------------------------------

            LLM_REQUESTS_TOTAL.labels(
                service=self.SERVICE_NAME,
                model=self.model,
                status="error",
            ).inc()

            logger.exception(
                "RAG generation failed."
            )

            raise RuntimeError(
                "Failed to generate response."
            ) from exc

        # ======================================================
        # SAVE CONVERSATION MEMORY
        # ======================================================

        await conversation_memory.add_message(
            conversation_id=conversation_id,
            role="user",
            content=message,
        )

        await conversation_memory.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=answer,
        )

        logger.debug(
            "Conversation saved."
        )

        return answer


rag_pipeline = RAGPipeline()