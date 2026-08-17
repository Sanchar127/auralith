from __future__ import annotations

import pytest_asyncio

from app.services.chat.memory import conversation_memory
from app.services.rag.pipeline import rag_pipeline
from app.services.rag.vector_store import vector_store


@pytest_asyncio.fixture(
    scope="session",
)
async def rag_services():
    """
    Initialize the complete RAG service stack once
    for the entire evaluation test session.

    The services are global singletons, so they must
    remain alive for all evaluation tests.
    """

    # ------------------------------------------------------
    # Startup
    # ------------------------------------------------------

    await conversation_memory.connect()

    await vector_store.connect()
    await vector_store.initialize()

    await rag_pipeline.connect()

    try:
        yield

    finally:
        # --------------------------------------------------
        # Shutdown
        # --------------------------------------------------

        await rag_pipeline.close()

        await vector_store.close()

        await conversation_memory.close()