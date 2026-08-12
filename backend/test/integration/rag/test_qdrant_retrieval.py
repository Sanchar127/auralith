
from __future__ import annotations

import pytest

from app.services.rag.indexer import rag_indexer
from app.services.rag.retriever import RAGRetriever
from app.services.rag.vector_store import vector_store


@pytest.fixture
async def qdrant():
    """
    Connect to Qdrant and ensure test data is indexed
    before each integration test.
    """

    await vector_store.connect()

    try:
        # Make sure the collection exists.
        await vector_store.initialize()

        # Index known test data so retrieval can be tested
        # against real vectors in Qdrant.
        await rag_indexer.index_document(
            text=(
                "Audio enhancement improves the quality of "
                "recordings by reducing background noise and "
                "improving speech clarity."
            ),
            metadata={
                "source": "integration_test",
                "category": "audio",
            },
        )

        yield vector_store

    finally:
        await vector_store.close()


@pytest.mark.asyncio
async def test_qdrant_collection_exists(qdrant):
    """
    Verify that the configured Qdrant collection exists.
    """

    client = qdrant._get_client()

    collections = await client.get_collections()

    collection_names = {
        collection.name
        for collection in collections.collections
    }

    assert qdrant.collection in collection_names


@pytest.mark.asyncio
async def test_qdrant_collection_has_points(qdrant):
    """
    Verify that the Qdrant collection contains indexed documents.

    Retrieval cannot work if the collection is empty.
    """

    client = qdrant._get_client()

    count_result = await client.count(
        collection_name=qdrant.collection,
        exact=True,
    )

    assert count_result.count > 0, (
        f"Qdrant collection '{qdrant.collection}' "
        "contains no indexed documents."
    )


@pytest.mark.asyncio
async def test_qdrant_returns_results(qdrant):
    """
    Verify that semantic retrieval returns documents
    for a real query.
    """

    retriever = RAGRetriever(
        top_k=5,
        score_threshold=0.0,
    )

    results = await retriever.retrieve(
        "audio enhancement"
    )

    assert results, (
        "RAG retrieval returned no results. "
        "Check embeddings and Qdrant indexing."
    )

    assert len(results) <= 5


@pytest.mark.asyncio
async def test_qdrant_results_have_required_fields(qdrant):
    """
    Verify that retrieved documents have the structure
    expected by the RAG pipeline.
    """

    retriever = RAGRetriever(
        top_k=5,
        score_threshold=0.0,
    )

    results = await retriever.retrieve(
        "audio enhancement"
    )

    assert results, (
        "RAG retrieval returned no results."
    )

    for result in results:
        assert "text" in result
        assert "score" in result
        assert "metadata" in result

        assert isinstance(
            result["text"],
            str,
        )

        assert isinstance(
            result["score"],
            (int, float),
        )

        assert isinstance(
            result["metadata"],
            dict,
        )

        assert result["text"].strip()

