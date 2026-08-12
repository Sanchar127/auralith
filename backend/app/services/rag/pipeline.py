from __future__ import annotations

from ollama import AsyncClient

from app.core.config import settings
from app.core.logger import logger

from app.services.chat.memory import conversation_memory
from app.services.chat.prompt_builder import prompt_builder
from app.services.rag.retriever import rag_retriever


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
    """

    def __init__(self) -> None:
        self.client: AsyncClient | None = None
        self.model = settings.OLLAMA_MODEL

    # ==========================================================
    # Lifecycle
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

        # AsyncClient does not require an explicit close in
        # every ollama-python version, so simply release it.
        self.client = None

        logger.info("Ollama client closed.")

    def _get_client(self) -> AsyncClient:
        """Return the initialized Ollama client."""

        if self.client is None:
            raise RuntimeError(
                "Ollama client is not initialized. "
                "Call connect() first."
            )

        return self.client

    # ==========================================================
    # RAG Pipeline
    # ==========================================================

    async def run(
        self,
        conversation_id: str,
        message: str,
    ) -> str:
        """Execute the complete RAG conversation pipeline."""

        logger.info(
            "Starting RAG pipeline."
        )

        client = self._get_client()

        # ----------------------------------------
        # Load conversation history
        # ----------------------------------------

        history = await conversation_memory.get_messages(
            conversation_id
        )

        logger.debug(
            "Loaded %s previous messages.",
            len(history),
        )

        # ----------------------------------------
        # Retrieve knowledge from Qdrant
        # ----------------------------------------

        context = await rag_retriever.retrieve_context(
            message
        )

        logger.debug(
            "Retrieved context length=%s",
            len(context),
        )

        # ----------------------------------------
        # Build Ollama messages
        # ----------------------------------------

        messages = prompt_builder.build(
            message=message,
            context=context,
            history=history,
        )

        logger.debug(
            "Prompt built with %s messages.",
            len(messages),
        )

        # ----------------------------------------
        # Generate response using Ollama
        # ----------------------------------------

        try:
            response = await client.chat(
                model=self.model,
                messages=messages,
            )

            answer = response["message"]["content"]

            logger.info(
                "RAG response generated successfully."
            )

        except Exception as exc:
            logger.exception(
                "RAG generation failed."
            )

            raise RuntimeError(
                "Failed to generate response."
            ) from exc

        # ----------------------------------------
        # Save conversation memory
        # ----------------------------------------

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