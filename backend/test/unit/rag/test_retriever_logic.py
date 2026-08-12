import pytest

from app.services.rag.retriever import (
    RAGRetriever,
)


@pytest.mark.asyncio
async def test_empty_query_returns_empty():

    retriever = RAGRetriever()

    result = await retriever.retrieve(
        "   "
    )

    assert result == []


@pytest.mark.asyncio
async def test_low_score_results_are_filtered(
    monkeypatch,
):

    class FakeEmbeddingService:

        async def embed(self, query):
            return [0.1, 0.2, 0.3]

    class FakeResult:

        id = "chunk-1"
        score = 0.20

        payload = {
            "text": "irrelevant document"
        }

    class FakeVectorStore:

        async def search(
            self,
            embedding,
            limit,
        ):
            return [
                FakeResult()
            ]

    monkeypatch.setattr(
        "app.services.rag.retriever.embedding_service",
        FakeEmbeddingService(),
    )

    monkeypatch.setattr(
        "app.services.rag.retriever.vector_store",
        FakeVectorStore(),
    )

    retriever = RAGRetriever(
        top_k=5,
        score_threshold=0.35,
    )

    results = await retriever.retrieve(
        "test query"
    )

    assert results == []


@pytest.mark.asyncio
async def test_relevant_result_is_returned(
    monkeypatch,
):

    class FakeEmbeddingService:

        async def embed(self, query):
            return [0.1, 0.2, 0.3]

    class FakeResult:

        id = "chunk-123"
        score = 0.90

        payload = {
            "text": "Auralith audio enhancement"
        }

    class FakeVectorStore:

        async def search(
            self,
            embedding,
            limit,
        ):
            return [
                FakeResult()
            ]

    monkeypatch.setattr(
        "app.services.rag.retriever.embedding_service",
        FakeEmbeddingService(),
    )

    monkeypatch.setattr(
        "app.services.rag.retriever.vector_store",
        FakeVectorStore(),
    )

    retriever = RAGRetriever(
        top_k=5,
        score_threshold=0.35,
    )

    results = await retriever.retrieve(
        "What is audio enhancement?"
    )

    assert len(results) == 1

    assert (
        results[0]["chunk_id"]
        == "chunk-123"
    )

    assert (
        results[0]["score"]
        == 0.90
    )