from __future__ import annotations

from typing import Any

from app.core.logger import logger
from app.services.rag.embeddings import embedding_service
from app.services.rag.vector_store import vector_store


class RAGRetriever:
    """
    Retrieves relevant knowledge from Qdrant.

    Responsibilities:

    1. Generate query embeddings.
    2. Search Qdrant.
    3. Filter low-relevance results.
    4. Resolve chunk IDs.
    5. Normalize retrieved documents.
    6. Remove duplicate chunks.
    7. Sort results by relevance score.
    8. Format retrieved documents for the LLM.
    """

    def __init__(
        self,
        top_k: int = 5,
        score_threshold: float = 0.35,
    ) -> None:
        self.top_k = top_k
        self.score_threshold = score_threshold

    # ==========================================================
    # Retrieval
    # ==========================================================

    async def retrieve(
        self,
        query: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant chunks for a query.

        Duplicate chunk IDs are removed. If multiple Qdrant
        points contain the same chunk_id, only the result
        with the highest relevance score is retained.

        Args:
            query: User search query.

        Returns:
            A list of normalized unique documents ordered
            by descending relevance score.
        """

        # ------------------------------------------------------
        # Validate query
        # ------------------------------------------------------

        if not query or not query.strip():
            return []

        logger.info(
            "Retrieving context for query."
        )

        # ------------------------------------------------------
        # Generate query embedding
        # ------------------------------------------------------

        query_embedding = await embedding_service.embed(
            query
        )

        # ------------------------------------------------------
        # Search Qdrant
        # ------------------------------------------------------

        results = await vector_store.search(
            embedding=query_embedding,
            limit=self.top_k,
        )

        # ------------------------------------------------------
        # Deduplicated documents
        #
        # Key:
        #     chunk_id
        #
        # Value:
        #     highest-scoring document for that chunk
        # ------------------------------------------------------

        documents_by_chunk_id: dict[
            str,
            dict[str, Any],
        ] = {}

        # ------------------------------------------------------
        # Process Qdrant results
        # ------------------------------------------------------

        for result in results:
            score = float(result.score)

            # --------------------------------------------------
            # Filter low-relevance results
            # --------------------------------------------------

            if score < self.score_threshold:
                continue

            payload = result.payload or {}

            # --------------------------------------------------
            # Resolve chunk ID
            #
            # Prefer payload.chunk_id.
            # Fall back to Qdrant point ID.
            # --------------------------------------------------

            payload_chunk_id = payload.get(
                "chunk_id"
            )

            if payload_chunk_id is not None:
                chunk_id = str(
                    payload_chunk_id
                )

            elif result.id is not None:
                chunk_id = str(
                    result.id
                )

            else:
                logger.warning(
                    "Qdrant result has no usable "
                    "chunk_id. Skipping result."
                )
                continue

            # --------------------------------------------------
            # Extract text
            # --------------------------------------------------

            text = payload.get(
                "text",
                "",
            )

            if not isinstance(text, str):
                text = str(text)

            text = text.strip()

            if not text:
                logger.warning(
                    "Qdrant result %s has empty text. "
                    "Skipping result.",
                    chunk_id,
                )
                continue

            # --------------------------------------------------
            # Extract metadata
            # --------------------------------------------------

            metadata = {
                key: value
                for key, value in payload.items()
                if key not in {
                    "text",
                    "chunk_id",
                }
            }

            # --------------------------------------------------
            # Build normalized document
            # --------------------------------------------------

            document: dict[str, Any] = {
                "chunk_id": chunk_id,
                "text": text,
                "score": score,
                "metadata": metadata,
            }

            # --------------------------------------------------
            # Deduplicate
            # --------------------------------------------------
            #
            # Same chunk may exist multiple times in Qdrant.
            #
            # Example:
            #
            # chunk-123 score=0.91
            # chunk-123 score=0.87
            # chunk-123 score=0.72
            #
            # Keep only:
            #
            # chunk-123 score=0.91
            # --------------------------------------------------

            existing_document = (
                documents_by_chunk_id.get(
                    chunk_id
                )
            )

            if existing_document is None:
                documents_by_chunk_id[
                    chunk_id
                ] = document

                continue

            existing_score = float(
                existing_document["score"]
            )

            if score > existing_score:
                logger.debug(
                    "Replacing duplicate chunk '%s' "
                    "with higher-scoring result: "
                    "%.4f -> %.4f",
                    chunk_id,
                    existing_score,
                    score,
                )

                documents_by_chunk_id[
                    chunk_id
                ] = document

            else:
                logger.debug(
                    "Ignoring duplicate chunk '%s' "
                    "with lower score %.4f.",
                    chunk_id,
                    score,
                )

        # ------------------------------------------------------
        # Convert dictionary to list
        # ------------------------------------------------------

        documents = list(
            documents_by_chunk_id.values()
        )

        # ------------------------------------------------------
        # Explicitly order by relevance
        # ------------------------------------------------------
        #
        # Even though Qdrant normally returns results ordered
        # by score, we enforce the contract here.
        # ------------------------------------------------------

        documents.sort(
            key=lambda document: float(
                document["score"]
            ),
            reverse=True,
        )

        logger.info(
            "Retrieved %d unique relevant chunks.",
            len(documents),
        )

        return documents

    # ==========================================================
    # Context generation
    # ==========================================================

    async def retrieve_context(
        self,
        query: str,
    ) -> str:
        """
        Retrieve relevant documents and convert them
        into LLM-ready context.

        Each context block includes the chunk ID so the
        model can identify which retrieved source supports
        its answer.
        """

        documents = await self.retrieve(query)

        if not documents:
            return ""

        context_parts: list[str] = []

        for index, document in enumerate(
            documents,
            start=1,
        ):
            chunk_id = document["chunk_id"]
            text = document["text"]

            context_parts.append(
                f"[Source {index}]\n"
                f"chunk_id: {chunk_id}\n"
                f"content:\n{text}"
            )

        return "\n\n".join(context_parts)

rag_retriever = RAGRetriever()