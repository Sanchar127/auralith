
from __future__ import annotations

import pytest

from app.services.rag.indexer import RAGIndexer


@pytest.mark.asyncio
async def test_index_document_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    indexer = RAGIndexer()

    async def mock_embed_many(
        texts: list[str],
    ) -> list[list[float]]:
        return [
            [0.1, 0.2, 0.3]
            for _ in texts
        ]

    captured: dict = {}

    async def mock_add_many(
        *,
        embeddings,
        texts,
        metadatas,
    ) -> None:
        captured["embeddings"] = embeddings
        captured["texts"] = texts
        captured["metadatas"] = metadatas

    monkeypatch.setattr(
        "app.services.rag.indexer.embedding_service.embed_many",
        mock_embed_many,
    )

    monkeypatch.setattr(
        "app.services.rag.indexer.vector_store.add_many",
        mock_add_many,
    )

    result = await indexer.index_document(
        text=(
            "Audio enhancement improves "
            "the quality of an audio recording."
        ),
        metadata={
            "source": "test",
        },
    )

    assert result["success"] is True
    assert result["chunks"] > 0

    assert len(captured["embeddings"]) == result["chunks"]
    assert len(captured["texts"]) == result["chunks"]
    assert len(captured["metadatas"]) == result["chunks"]


@pytest.mark.asyncio
async def test_index_document_empty_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    indexer = RAGIndexer()

    embed_called = False
    store_called = False

    async def mock_embed_many(
        texts: list[str],
    ) -> list[list[float]]:
        nonlocal embed_called

        embed_called = True

        return []

    async def mock_add_many(
        *,
        embeddings,
        texts,
        metadatas,
    ) -> None:
        nonlocal store_called

        store_called = True

    monkeypatch.setattr(
        "app.services.rag.indexer.embedding_service.embed_many",
        mock_embed_many,
    )

    monkeypatch.setattr(
        "app.services.rag.indexer.vector_store.add_many",
        mock_add_many,
    )

    result = await indexer.index_document(
        text="",
    )

    assert result == {
        "success": False,
        "chunks": 0,
    }

    assert embed_called is False
    assert store_called is False


@pytest.mark.asyncio
async def test_index_document_passes_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    indexer = RAGIndexer()

    captured: dict = {}

    async def mock_embed_many(
        texts: list[str],
    ) -> list[list[float]]:
        return [
            [0.1, 0.2, 0.3]
            for _ in texts
        ]

    async def mock_add_many(
        *,
        embeddings,
        texts,
        metadatas,
    ) -> None:
        captured["metadatas"] = metadatas

    monkeypatch.setattr(
        "app.services.rag.indexer.embedding_service.embed_many",
        mock_embed_many,
    )

    monkeypatch.setattr(
        "app.services.rag.indexer.vector_store.add_many",
        mock_add_many,
    )

    metadata = {
        "source": "knowledge-base",
        "document_id": "doc-123",
    }

    await indexer.index_document(
        text="Auralith generates music.",
        metadata=metadata,
    )

    assert captured["metadatas"]

    for chunk_metadata in captured["metadatas"]:
        assert chunk_metadata["source"] == "knowledge-base"
        assert chunk_metadata["document_id"] == "doc-123"


@pytest.mark.asyncio
async def test_index_documents_indexes_all_documents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    indexer = RAGIndexer()

    indexed_documents: list[str] = []

    async def mock_index_document(
        *,
        text: str,
        metadata=None,
    ) -> dict:
        indexed_documents.append(text)

        return {
            "success": True,
            "chunks": 2,
        }

    monkeypatch.setattr(
        indexer,
        "index_document",
        mock_index_document,
    )

    documents = [
        {
            "text": "Audio enhancement content.",
            "metadata": {
                "source": "audio",
            },
        },
        {
            "text": "Song generation content.",
            "metadata": {
                "source": "music",
            },
        },
        {
            "text": "Supported audio formats.",
            "metadata": {
                "source": "formats",
            },
        },
    ]

    result = await indexer.index_documents(
        documents
    )

    assert result["success"] is True
    assert result["documents"] == 3
    assert result["chunks"] == 6

    assert indexed_documents == [
        "Audio enhancement content.",
        "Song generation content.",
        "Supported audio formats.",
    ]


@pytest.mark.asyncio
async def test_index_documents_empty_list() -> None:
    indexer = RAGIndexer()

    result = await indexer.index_documents([])

    assert result == {
        "success": True,
        "documents": 0,
        "chunks": 0,
    }

