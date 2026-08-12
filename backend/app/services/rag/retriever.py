
from __future__ import annotations

from typing import Any

from app.core.logger import logger
from app.services.rag.embeddings import embedding_service
from app.services.rag.vector_store import vector_store


class RAGRetriever:
    """
    Retrieves relevant knowledge from Qdrant.

    The chunk identifier can come from either:

    1. The payload's ``chunk_id`` field.
    2. The Qdrant point ID.

    This keeps retrieval compatible with both indexed
    production documents and unit-test fixtures.
    """

    def __init__(
        self,
        top_k: int = 5,
        score_threshold: float = 0.35,
    ) -> None:
        self.top_k = top_k
        self.score_threshold = score_threshold

    async def retrieve(
        self,
        query: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: User's search query.

        Returns:
            A list of normalized retrieved documents.
        """

        # Ignore empty or whitespace-only queries.
        if not query.strip():
            return []

        logger.info("Retrieving context for query.")

        # Generate embedding for the query.
        query_embedding = await embedding_service.embed(query)

        # Search Qdrant using the generated embedding.
        results = await vector_store.search(
            embedding=query_embedding,
            limit=self.top_k,
        )

        documents: list[dict[str, Any]] = []

        for result in results:
            score = float(result.score)

            # Filter low-relevance results.
            if score < self.score_threshold:
                continue

            payload = result.payload or {}

            # --------------------------------------------------
            # Resolve chunk ID
            # --------------------------------------------------
            #
            # Prefer the explicit chunk_id stored in the payload.
            # Fall back to the Qdrant point ID.
            # --------------------------------------------------

            payload_chunk_id = payload.get("chunk_id")

            if payload_chunk_id is not None:
                chunk_id = str(payload_chunk_id)

            elif result.id is not None:
                chunk_id = str(result.id)

            else:
                logger.warning(
                    "Qdrant result has no usable chunk_id."
                )
                continue

            # --------------------------------------------------
            # Extract text
            # --------------------------------------------------

            text = payload.get("text", "")

            if not isinstance(text, str):
                text = str(text)

            if not text.strip():
                logger.warning(
                    "Qdrant result %s has empty text.",
                    chunk_id,
                )
                continue

            # --------------------------------------------------
            # Extract metadata
            # --------------------------------------------------

            metadata = {
                key: value
                for key, value in payload.items()
                if key not in {"text", "chunk_id"}
            }

            # --------------------------------------------------
            # Build normalized retrieval result
            # --------------------------------------------------

            documents.append(
                {
                    "chunk_id": chunk_id,
                    "text": text,
                    "score": score,
                    "metadata": metadata,
                }
            )

        logger.info(
            "Retrieved %s relevant chunks.",
            len(documents),
        )

        return documents

    async def retrieve_context(
        self,
        query: str,
    ) -> str:
        """
        Convert retrieved documents into LLM-ready context.

        Args:
            query: User's search query.

        Returns:
            Formatted context string suitable for an LLM prompt.
        """

        documents = await self.retrieve(query)

        if not documents:
            return ""

        context_parts: list[str] = []

        for index, document in enumerate(
            documents,
            start=1,
        ):
            context_parts.append(
                f"Context {index}:\n\n"
                f"{document['text']}"
            )

        return "\n\n".join(context_parts)


rag_retriever = RAGRetriever()
