from __future__ import annotations

import asyncio

from ollama import AsyncClient

from app.core.config import settings
from app.core.logger import logger


class EmbeddingService:
    """
    Generates vector embeddings using Ollama.

    This service is isolated from the rest of the
    RAG pipeline so the embedding provider can be
    replaced without changing other components.
    """

    MAX_RETRIES = 3

    def __init__(self) -> None:

        self.client = AsyncClient(
            host=settings.OLLAMA_BASE_URL,
        )

        self.model = settings.OLLAMA_EMBED_MODEL

    async def embed(
        self,
        text: str,
    ) -> list[float]:
        """
        Generate an embedding for a single text.
        """

        text = text.strip()

        if not text:
            raise ValueError(
                "Cannot embed empty text."
            )

        logger.debug(
            "Generating embedding (%d chars).",
            len(text),
        )

        last_error: Exception | None = None

        for attempt in range(
            1,
            self.MAX_RETRIES + 1,
        ):

            try:

                response = (
                    await self.client.embeddings(
                        model=self.model,
                        prompt=text,
                    )
                )

                embedding = response.get(
                    "embedding"
                )

                if not embedding:

                    raise RuntimeError(
                        "Embedding response was empty."
                    )

                logger.debug(
                    "Embedding generated successfully."
                )

                return embedding

            except Exception as exc:

                last_error = exc

                logger.warning(
                    "Embedding failed (%d/%d).",
                    attempt,
                    self.MAX_RETRIES,
                )

                await asyncio.sleep(1)

        raise RuntimeError(
            "Failed to generate embedding."
        ) from last_error

    async def embed_many(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Ollama currently processes embedding
        requests individually, so we parallelize
        them with asyncio.
        """

        if not texts:
            return []

        logger.info(
            "Generating %d embeddings.",
            len(texts),
        )

        embeddings = await asyncio.gather(
            *[
                self.embed(text)
                for text in texts
            ]
        )

        logger.info(
            "Generated %d embeddings.",
            len(embeddings),
        )

        return embeddings


embedding_service = EmbeddingService()