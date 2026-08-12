
from __future__ import annotations

import pytest

from app.services.rag.embeddings import EmbeddingService


@pytest.mark.asyncio
async def test_embed_returns_embedding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = EmbeddingService()

    expected_embedding = [
        0.1,
        0.2,
        0.3,
        0.4,
    ]

    async def mock_embed(
        text: str,
    ) -> list[float]:
        return expected_embedding

    monkeypatch.setattr(
        service,
        "embed",
        mock_embed,
    )

    result = await service.embed(
        "audio enhancement"
    )

    assert result == expected_embedding
    assert isinstance(result, list)

    assert all(
        isinstance(value, float)
        for value in result
    )


@pytest.mark.asyncio
async def test_embed_many_returns_embeddings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = EmbeddingService()

    async def mock_embed(
        text: str,
    ) -> list[float]:
        return [float(len(text))]

    monkeypatch.setattr(
        service,
        "embed",
        mock_embed,
    )

    texts = [
        "audio enhancement",
        "song generation",
        "supported audio formats",
    ]

    results = await service.embed_many(texts)

    assert len(results) == len(texts)

    for result in results:
        assert isinstance(result, list)
        assert result


@pytest.mark.asyncio
async def test_embed_many_preserves_input_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = EmbeddingService()

    async def mock_embed(
        text: str,
    ) -> list[float]:
        return [float(len(text))]

    monkeypatch.setattr(
        service,
        "embed",
        mock_embed,
    )

    texts = [
        "short",
        "this is longer",
        "medium text",
    ]

    results = await service.embed_many(texts)

    expected = [
        [float(len(text))]
        for text in texts
    ]

    assert results == expected


@pytest.mark.asyncio
async def test_embed_many_empty_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = EmbeddingService()

    async def mock_embed(
        text: str,
    ) -> list[float]:
        return [1.0]

    monkeypatch.setattr(
        service,
        "embed",
        mock_embed,
    )

    results = await service.embed_many([])

    assert results == []


@pytest.mark.asyncio
async def test_embed_many_calls_embed_for_each_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = EmbeddingService()

    calls: list[str] = []

    async def mock_embed(
        text: str,
    ) -> list[float]:
        calls.append(text)

        return [
            1.0,
            2.0,
        ]

    monkeypatch.setattr(
        service,
        "embed",
        mock_embed,
    )

    texts = [
        "first",
        "second",
        "third",
    ]

    results = await service.embed_many(texts)

    assert calls == texts
    assert len(results) == 3

