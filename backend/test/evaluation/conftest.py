from __future__ import annotations

import pytest_asyncio

from app.services.chat.memory import conversation_memory
from app.services.rag.pipeline import rag_pipeline
from app.services.rag.vector_store import vector_store


@pytest_asyncio.fixture(
    scope="session",
    autouse=True,
)
async def rag_services():
    """Initialize RAG services for the evaluation session."""

    await conversation_memory.connect()

    await vector_store.connect()
    await vector_store.initialize()

    rag_pipeline.connect()

    yield

    await rag_pipeline.close()
    await vector_store.close()
    await conversation_memory.close()