from __future__ import annotations

from typing import Any

from app.core.logger import logger
from app.services.rag.embeddings import embedding_service
from app.services.rag.vector_store import vector_store


class RAGRetriever:
    """
    Retrieves relevant knowledge from Qdrant.
    """

    def __init__(
        self,
        top_k: int = 5,
        score_threshold: float = 0.35,
    ):
        self.top_k = top_k
        self.score_threshold = score_threshold


    async def retrieve(
        self,
        query: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant chunks for a query.

        Args:
            query:
                User question/message

        Returns:
            List of matching documents
        """

        if not query.strip():
            return []


        logger.info(
            "Retrieving context for query."
        )


        # ----------------------------------
        # Create query embedding
        # ----------------------------------

        query_embedding = (
            await embedding_service.embed(
                query
            )
        )


        # ----------------------------------
        # Search Qdrant
        # ----------------------------------

        results = await vector_store.search(
            embedding=query_embedding,
            limit=self.top_k,
        )


        documents = []


        for result in results:

            score = result.score


            # Skip weak matches
            if (
                score
                < self.score_threshold
            ):
                continue


            payload = (
                result.payload
                or {}
            )


            documents.append(
                {
                    "text": payload.get(
                        "text",
                        "",
                    ),

                    "score": score,

                    "metadata": {
                        key: value
                        for key, value
                        in payload.items()
                        if key != "text"
                    },
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
        Convert retrieved documents into
        LLM-ready context.
        """

        documents = await self.retrieve(
            query
        )


        if not documents:
            return ""


        context_parts = []


        for index, document in enumerate(
            documents,
            start=1,
        ):

            context_parts.append(
                f"""
Context {index}:

{document['text']}
"""
            )


        return "\n".join(
            context_parts
        )


rag_retriever = RAGRetriever()