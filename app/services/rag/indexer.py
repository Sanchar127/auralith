from __future__ import annotations

from typing import Any

from app.core.logger import logger
from app.services.rag.chunker import chunker
from app.services.rag.embeddings import embedding_service
from app.services.rag.vector_store import vector_store


class RAGIndexer:
    """
    Handles indexing documents into the vector database.
    """

    async def index_document(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        """
        Index a single document.

        Steps:
            1. Split document into chunks
            2. Generate embeddings
            3. Store vectors in Qdrant
        """

        logger.info(
            "Starting document indexing."
        )

        chunks = chunker.split(
            text=text,
            metadata=metadata,
        )

        if not chunks:
            logger.warning(
                "No chunks created. Skipping."
            )

            return {
                "success": False,
                "chunks": 0,
            }


        texts = [
            chunk.text
            for chunk in chunks
        ]

        metadatas = [
            chunk.metadata
            for chunk in chunks
        ]


        logger.info(
            "Generating embeddings for %s chunks.",
            len(texts),
        )


        embeddings = (
            await embedding_service.embed_many(
                texts
            )
        )


        logger.info(
            "Storing vectors in Qdrant."
        )


        await vector_store.add_many(
            embeddings=embeddings,
            texts=texts,
            metadatas=metadatas,
        )


        logger.info(
            "Document indexing completed."
        )


        return {
            "success": True,
            "chunks": len(chunks),
        }


    async def index_documents(
        self,
        documents: list[dict],
    ) -> dict:
        """
        Index multiple documents.

        Expected format:

        [
            {
                "text": "...",
                "metadata": {
                    "source": "lyrics"
                }
            }
        ]
        """

        total_chunks = 0


        for document in documents:

            result = await self.index_document(
                text=document["text"],
                metadata=document.get(
                    "metadata",
                    {},
                ),
            )

            total_chunks += result.get(
                "chunks",
                0,
            )


        return {
            "success": True,
            "documents": len(documents),
            "chunks": total_chunks,
        }


rag_indexer = RAGIndexer()