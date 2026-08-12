
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
async def test_index_document_end_to_end(qdrant_connection):
    """
    Verify the complete indexing flow:

        document
            ↓
        chunker
            ↓
        Ollama embeddings
            ↓
        Qdrant
            ↓
        retriever
    """

    unique_marker = f"indexing-test-{uuid4().hex}"

    text = (
        f"{unique_marker}. "
        "Retrieval augmented generation combines "
        "retrieval with language model generation."
    )

    result = await rag_indexer.index_document(
        text=text,
        metadata={
            "source": "integration-test",
            "test_id": unique_marker,
        },
    )

    assert result["success"] is True
    assert result["chunks"] >= 1

    documents = await rag_retriever.retrieve(unique_marker)

    assert documents

    matching_documents = [
        document
        for document in documents
        if unique_marker in document["text"]
    ]

    assert matching_documents

    document = matching_documents[0]

    assert document["text"]
    assert document["score"] >= rag_retriever.score_threshold
    assert document["chunk_id"]


@pytest.mark.asyncio
async def test_index_multiple_documents_end_to_end(
    qdrant_connection,
):
    """Verify that multiple documents are indexed."""

    marker_one = f"document-one-{uuid4().hex}"
    marker_two = f"document-two-{uuid4().hex}"

    documents = [
        {
            "text": (
                f"{marker_one}. "
                "This document contains information "
                "about semantic search."
            ),
            "metadata": {
                "source": "integration-test",
                "test_id": marker_one,
            },
        },
        {
            "text": (
                f"{marker_two}. "
                "This document contains information "
                "about vector databases."
            ),
            "metadata": {
                "source": "integration-test",
                "test_id": marker_two,
            },
        },
    ]

    result = await rag_indexer.index_documents(documents)

    assert result["success"] is True
    assert result["documents"] == 2
    assert result["chunks"] >= 2

    first_results = await rag_retriever.retrieve(marker_one)
    second_results = await rag_retriever.retrieve(marker_two)

    assert first_results
    assert second_results

    assert any(
        marker_one in document["text"]
        for document in first_results
    )

    assert any(
        marker_two in document["text"]
        for document in second_results
    )


@pytest.mark.asyncio
async def test_index_document_preserves_metadata(
    qdrant_connection,
):
    """Verify metadata survives indexing and retrieval."""

    marker = f"metadata-test-{uuid4().hex}"

    result = await rag_indexer.index_document(
        text=(
            f"{marker}. "
            "Metadata should remain attached "
            "to the indexed chunk."
        ),
        metadata={
            "source": "integration-test",
            "document_type": "test",
            "test_id": marker,
        },
    )

    assert result["success"] is True
    assert result["chunks"] >= 1

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
    assert metadata["document_type"] == "test"
    assert metadata["test_id"] == marker


@pytest.mark.asyncio
async def test_index_empty_document(qdrant_connection):
    """Verify empty documents are skipped."""

    result = await rag_indexer.index_document(
        text="",
        metadata={
            "source": "integration-test",
        },
    )

    assert result["success"] is False
    assert result["chunks"] == 0


@pytest.mark.asyncio
async def test_index_documents_empty_list(
    qdrant_connection,
):
    """Verify indexing an empty document list."""

    result = await rag_indexer.index_documents([])

    assert result["success"] is True
    assert result["documents"] == 0
    assert result["chunks"] == 0

