from __future__ import annotations

from typing import Any

from app.core.logger import logger


class Reranker:
    """
    Evaluation-level reranker.

    The existing RAGRetriever remains completely unchanged.

    Input:
        Documents returned by:

            await rag_retriever.retrieve(query)

    Output:
        Reranked documents containing:

            chunk_id
            text
            metadata
            score
            retrieval_score
            rerank_score

    The current implementation uses the existing retrieval
    score as the reranking signal.

    This gives us a stable baseline for reranking evaluation.
    A semantic/cross-encoder reranker can replace the scoring
    implementation later without changing the retriever API.
    """

    def __init__(self) -> None:
        pass

    # ==========================================================
    # Reranking
    # ==========================================================

    def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Rerank retrieved documents.

        Args:
            query:
                Original user query.

            documents:
                Documents returned by RAGRetriever.retrieve().

            top_k:
                Optional number of documents to return.

        Returns:
            Reranked documents ordered by rerank_score.
        """

        if not documents:
            return []

        if not query or not query.strip():
            return documents[:top_k] if top_k else documents.copy()

        logger.info(
            "Reranking %d retrieved documents.",
            len(documents),
        )

        reranked_documents: list[dict[str, Any]] = []

        # ------------------------------------------------------
        # Prepare documents
        # ------------------------------------------------------

        for document in documents:

            # --------------------------------------------------
            # Copy the document.
            #
            # Never mutate the original retriever result.
            # --------------------------------------------------

            reranked_document = document.copy()

            # --------------------------------------------------
            # Preserve the original retrieval score.
            #
            # Retriever currently returns:
            #
            #     "score": 0.8492
            #
            # Evaluation expects:
            #
            #     "retrieval_score": 0.8492
            # --------------------------------------------------

            retrieval_score = float(
                document.get("score", 0.0)
            )

            reranked_document[
                "retrieval_score"
            ] = retrieval_score

            # --------------------------------------------------
            # Current baseline reranking score.
            #
            # Since we don't have a semantic reranker yet,
            # use retrieval score as the baseline rerank score.
            # --------------------------------------------------

            rerank_score = retrieval_score

            reranked_document[
                "rerank_score"
            ] = rerank_score

            reranked_documents.append(
                reranked_document
            )

        # ------------------------------------------------------
        # Sort by reranking score
        # ------------------------------------------------------

        reranked_documents.sort(
            key=lambda document: float(
                document["rerank_score"]
            ),
            reverse=True,
        )

        # ------------------------------------------------------
        # Apply top-K after reranking
        # ------------------------------------------------------

        if top_k is not None:

            if top_k <= 0:
                return []

            reranked_documents = (
                reranked_documents[:top_k]
            )

        logger.info(
            "Reranking completed successfully."
        )

        return reranked_documents


# ==========================================================
# Global instance
# ==========================================================

reranker = Reranker()