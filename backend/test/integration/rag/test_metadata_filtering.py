
from __future__ import annotations

from uuid import uuid4

import pytest

from app.services.rag.indexer import rag_indexer
from app.services.rag.retriever import rag_retriever
from app.services.rag.vector_store import vector_store


@pytest.fixture
async def qdrant_connection():
    """Connect to the real Qdrant service."""

    await vector_store.connect()
    await vector_store.initialize()

    yield

    await vector_store.close()


@pytest.mark.asyncio
async def test_metadata_is_stored_and_returned(
    qdrant_connection,
):
    """
    Verify metadata is preserved through:

        Indexer → Qdrant → Retriever
    """

    marker = f"metadata-filter-{uuid4().hex}"

    await rag_indexer.index_document(
        text=(
            f"{marker}. "
            "This document is used to verify metadata "
            "handling in the RAG system."
        ),
        metadata={
            "source": "integration-test",
            "category": "music",
            "language": "en",
            "test_id": marker,
        },
    )

    results = await rag_retriever.retrieve(marker)

    assert results

    matching = [
        document
        for document in results
        if marker in document["text"]
    ]

    assert matching

    metadata = matching[0]["metadata"]

    assert metadata["source"] == "integration-test"
    assert metadata["category"] == "music"
    assert metadata["language"] == "en"
    assert metadata["test_id"] == marker


@pytest.mark.asyncio
async def test_different_metadata_values_remain_distinct(
    qdrant_connection,
):
    """Verify metadata belonging to different documents is preserved."""

    marker_music = f"music-{uuid4().hex}"
    marker_technology = f"technology-{uuid4().hex}"

    await rag_indexer.index_documents(
        [
            {
                "text": (
                    f"{marker_music}. "
                    "Music retrieval and song generation."
                ),
                "metadata": {
                    "source": "integration-test",
                    "category": "music",
                    "test_id": marker_music,
                },
            },
            {
                "text": (
                    f"{marker_technology}. "
                    "Technology and software engineering."
                ),
                "metadata": {
                    "source": "integration-test",
                    "category": "technology",
                    "test_id": marker_technology,
                },
            },
        ]
    )

    music_results = await rag_retriever.retrieve(marker_music)
    technology_results = await rag_retriever.retrieve(
        marker_technology
    )

    assert music_results
    assert technology_results

    music_document = next(
        document
        for document in music_results
        if marker_music in document["text"]
    )

    technology_document = next(
        document
        for document in technology_results
        if marker_technology in document["text"]
    )

    assert music_document["metadata"]["category"] == "music"

    assert (
        technology_document["metadata"]["category"]
        == "technology"
    )

    assert (
        music_document["metadata"]["test_id"]
        == marker_music
    )

    assert (
        technology_document["metadata"]["test_id"]
        == marker_technology
    )


@pytest.mark.asyncio
async def test_metadata_does_not_replace_document_text(
    qdrant_connection,
):
    """Verify text and metadata remain separate fields."""

    marker = f"text-metadata-{uuid4().hex}"

    await rag_indexer.index_document(
        text=f"{marker}. Actual document content.",
        metadata={
            "source": "integration-test",
            "category": "test",
            "description": "metadata value",
        },
    )

    results = await rag_retriever.retrieve(marker)

    assert results

    document = next(
        document
        for document in results
        if marker in document["text"]
    )

    assert marker in document["text"]

    assert (
        document["metadata"]["description"]
        == "metadata value"
    )

    assert (
        document["metadata"]["description"]
        not in document["text"]
    )


@pytest.mark.asyncio
async def test_metadata_values_are_returned_with_correct_types(
    qdrant_connection,
):
    """Verify Qdrant metadata values remain usable."""

    marker = f"metadata-types-{uuid4().hex}"

    await rag_indexer.index_document(
        text=f"{marker}. Metadata type integration test.",
        metadata={
            "source": "integration-test",
            "chunk_number": 1,
            "published": True,
            "test_id": marker,
        },
    )

    results = await rag_retriever.retrieve(marker)

    assert results

    document = next(
        document
        for document in results
        if marker in document["text"]
    )

    metadata = document["metadata"]

    assert metadata["source"] == "integration-test"
    assert metadata["chunk_number"] == 1
    assert metadata["published"] is True
