
from __future__ import annotations

from uuid import uuid4

import pytest

from app.services.chat.memory import conversation_memory
from app.services.rag.indexer import rag_indexer
from app.services.rag.pipeline import rag_pipeline
from app.services.rag.vector_store import vector_store


@pytest.fixture
async def qdrant_connection():
    """Connect to the real Qdrant service."""

    await vector_store.connect()
    await vector_store.initialize()

    yield

    await vector_store.close()


@pytest.mark.asyncio
async def test_rag_pipeline_end_to_end(
    qdrant_connection,
):
    """
    Verify the complete RAG pipeline:

        User message
            ↓
        Conversation memory
            ↓
        Qdrant retrieval
            ↓
        Prompt builder
            ↓
        Ollama
            ↓
        Assistant response
            ↓
        Conversation memory
    """

    conversation_id = uuid4().hex
    marker = f"rag-pipeline-{uuid4().hex}"

    knowledge = (
        f"{marker}. "
        "Auralith uses retrieval augmented generation "
        "to provide context-aware responses."
    )

    await rag_indexer.index_document(
        text=knowledge,
        metadata={
            "source": "integration-test",
            "test_id": marker,
        },
    )

    question = f"What does the document say about {marker}?"

    answer = await rag_pipeline.run(
        conversation_id=conversation_id,
        message=question,
    )

    assert isinstance(answer, str)
    assert answer.strip()


@pytest.mark.asyncio
async def test_rag_pipeline_saves_conversation(
    qdrant_connection,
):
    """Verify user and assistant messages are saved."""

    conversation_id = uuid4().hex
    marker = f"conversation-save-{uuid4().hex}"

    await rag_indexer.index_document(
        text=(
            f"{marker}. "
            "This document is used to test conversation "
            "memory integration."
        ),
        metadata={
            "source": "integration-test",
            "test_id": marker,
        },
    )

    question = f"Explain {marker}."

    answer = await rag_pipeline.run(
        conversation_id=conversation_id,
        message=question,
    )

    assert isinstance(answer, str)
    assert answer.strip()

    history = await conversation_memory.get_messages(
        conversation_id
    )

    assert len(history) >= 2

    user_messages = [
        message
        for message in history
        if message.get("role") == "user"
    ]

    assistant_messages = [
        message
        for message in history
        if message.get("role") == "assistant"
    ]

    assert any(
        message.get("content") == question
        for message in user_messages
    )

    assert any(
        message.get("content") == answer
        for message in assistant_messages
    )


@pytest.mark.asyncio
async def test_rag_pipeline_uses_conversation_history(
    qdrant_connection,
):
    """
    Verify that the same conversation can be continued.

    The second request uses the conversation ID created
    by the first request.
    """

    conversation_id = uuid4().hex
    marker = f"history-{uuid4().hex}"

    await rag_indexer.index_document(
        text=(
            f"{marker}. "
            "The project name associated with this test "
            "is Auralith."
        ),
        metadata={
            "source": "integration-test",
            "test_id": marker,
        },
    )

    first_question = (
        f"What project is described in {marker}?"
    )

    first_answer = await rag_pipeline.run(
        conversation_id=conversation_id,
        message=first_question,
    )

    assert isinstance(first_answer, str)
    assert first_answer.strip()

    second_question = (
        "What was the project name you just mentioned?"
    )

    second_answer = await rag_pipeline.run(
        conversation_id=conversation_id,
        message=second_question,
    )

    assert isinstance(second_answer, str)
    assert second_answer.strip()

    history = await conversation_memory.get_messages(
        conversation_id
    )

    assert len(history) >= 4

    contents = [
        message.get("content")
        for message in history
    ]

    assert first_question in contents
    assert first_answer in contents
    assert second_question in contents
    assert second_answer in contents


@pytest.mark.asyncio
async def test_rag_pipeline_returns_string(
    qdrant_connection,
):
    """Verify the pipeline returns the generated answer as a string."""

    conversation_id = uuid4().hex

    answer = await rag_pipeline.run(
        conversation_id=conversation_id,
        message="What is retrieval augmented generation?",
    )

    assert isinstance(answer, str)
    assert answer.strip()
