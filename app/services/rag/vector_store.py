from __future__ import annotations

from typing import Any
from uuid import uuid4

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)

from app.core.config import settings
from app.core.logger import logger


class VectorStore:
    """
    Qdrant vector database service.
    """

    def __init__(self) -> None:

        self.client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
        )

        self.collection = settings.QDRANT_COLLECTION

        self.vector_size = settings.QDRANT_VECTOR_SIZE

    async def initialize(self) -> None:
        """
        Create the collection if it doesn't exist.
        """

        collections = await self.client.get_collections()

        names = {
            collection.name
            for collection in collections.collections
        }

        if self.collection in names:

            logger.info(
                "Qdrant collection '%s' already exists.",
                self.collection,
            )

            return

        logger.info(
            "Creating Qdrant collection '%s'.",
            self.collection,
        )

        await self.client.create_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE,
            ),
        )

        logger.info(
            "Collection created successfully."
        )

    async def add(
        self,
        embedding: list[float],
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Insert one document.
        """

        point_id = uuid4().hex

        payload = {
            "text": text,
            **(metadata or {}),
        }

        await self.client.upsert(
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
            "Inserted point %s",
            point_id,
        )

        return point_id

    async def add_many(
        self,
        embeddings: list[list[float]],
        texts: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """
        Bulk insert multiple documents.
        """

        points = []

        for embedding, text, metadata in zip(
            embeddings,
            texts,
            metadatas,
        ):
            points.append(
                PointStruct(
                    id=uuid4().hex,
                    vector=embedding,
                    payload={
                        "text": text,
                        **metadata,
                    },
                )
            )

        await self.client.upsert(
            collection_name=self.collection,
            points=points,
        )

        logger.info(
            "Inserted %d vectors.",
            len(points),
        )

    async def search(
        self,
        embedding: list[float],
        limit: int = 5,
    ):
        """
        Perform semantic search.
        Compatible with qdrant-client 1.18.x.
        """

        result = await self.client.query_points(
            collection_name=self.collection,
            query=embedding,
            limit=limit,
            with_payload=True,
        )

        return result.points

    async def delete(
        self,
        point_id: str,
    ) -> None:
        """
        Delete a vector by ID.
        """

        await self.client.delete(
            collection_name=self.collection,
            points_selector=[point_id],
        )

        logger.info(
            "Deleted point %s",
            point_id,
        )


vector_store = VectorStore()