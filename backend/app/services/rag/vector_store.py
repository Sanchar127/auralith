
from __future__ import annotations

from typing import Any
from uuid import uuid4

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    ScoredPoint,
    VectorParams,
)

from app.core.config import settings
from app.core.logger import logger


class VectorStore:
    """Qdrant vector database service."""

    def __init__(self) -> None:
        self.client: AsyncQdrantClient | None = None

        self.collection = settings.QDRANT_COLLECTION
        self.vector_size = settings.QDRANT_VECTOR_SIZE

    # ==========================================================
    # Connection lifecycle
    # ==========================================================

    async def connect(self) -> None:
        """Create the Qdrant client."""

        if self.client is not None:
            return

        self.client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
        )

        logger.info(
            "Connected to Qdrant at %s",
            settings.QDRANT_URL,
        )

    async def close(self) -> None:
        """Close the Qdrant client."""

        if self.client is None:
            return

        await self.client.close()

        self.client = None

        logger.info("Qdrant client closed.")

    def _get_client(self) -> AsyncQdrantClient:
        """Return the active Qdrant client."""

        if self.client is None:
            raise RuntimeError(
                "Qdrant client is not initialized. "
                "Call connect() first."
            )

        return self.client

    # ==========================================================
    # Collection management
    # ==========================================================

    async def initialize(self) -> None:
        """Create the collection if it does not exist."""

        client = self._get_client()

        collections = await client.get_collections()

        collection_names = {
            collection.name
            for collection in collections.collections
        }

        if self.collection in collection_names:
            logger.info(
                "Qdrant collection '%s' already exists.",
                self.collection,
            )
            return

        logger.info(
            "Creating Qdrant collection '%s'.",
            self.collection,
        )

        await client.create_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE,
            ),
        )

        logger.info(
            "Qdrant collection '%s' created successfully.",
            self.collection,
        )

    # ==========================================================
    # Insert
    # ==========================================================

    async def add(
        self,
        embedding: list[float],
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Insert one document into Qdrant."""

        client = self._get_client()

        point_id = uuid4().hex

        payload = {
            "text": text,
            **(metadata or {}),
        }

        await client.upsert(
            collection_name=self.collection,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
            ],
        )

        logger.debug(
            "Inserted Qdrant point %s.",
            point_id,
        )

        return point_id

    async def add_many(
        self,
        embeddings: list[list[float]],
        texts: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Bulk insert multiple documents."""

        client = self._get_client()

        if not (
            len(embeddings)
            == len(texts)
            == len(metadatas)
        ):
            raise ValueError(
                "embeddings, texts, and metadatas "
                "must have the same length."
            )

        points = []

        for embedding, text, metadata in zip(
            embeddings,
            texts,
            metadatas,
        ):
            payload = {
                "text": text,
                **metadata,
            }

            points.append(
                PointStruct(
                    id=uuid4().hex,
                    vector=embedding,
                    payload=payload,
                )
            )

        if not points:
            return

        await client.upsert(
            collection_name=self.collection,
            points=points,
        )

        logger.info(
            "Inserted %d vectors.",
            len(points),
        )
    # ==========================================================
    # Search
    # ==========================================================

    async def search(
        self,
        embedding: list[float],
        limit: int = 5,
    ) -> list[ScoredPoint]:
        """
        Perform semantic similarity search.

        Returns:
            List of Qdrant scored points ordered by relevance.
        """

        client = self._get_client()

        result = await client.query_points(
            collection_name=self.collection,
            query=embedding,
            limit=limit,
            with_payload=True,
        )

        return result.points

    # ==========================================================
    # Delete
    # ==========================================================

    async def delete(
        self,
        point_id: str,
    ) -> None:
        """Delete a vector by ID."""

        client = self._get_client()

        await client.delete(
            collection_name=self.collection,
            points_selector=[point_id],
        )

        logger.info(
            "Deleted Qdrant point %s.",
            point_id,
        )


vector_store = VectorStore()

