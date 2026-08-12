from __future__ import annotations

import re

import pytest

from app.services.rag.pipeline import rag_pipeline
from app.services.rag.retriever import rag_retriever


# ============================================================
# Test configuration
# ============================================================

QUERY = "What audio formats are supported?"

EXPECTED_FACTS = {
    "mp3",
    "wav",
}

KNOWN_WRONG_FACTS = {
    "flac",
    "aac",
    "ogg",
    "m4a",
}


# ============================================================
# Helpers
# ============================================================


def normalize_text(text: str) -> str:
    """
    Normalize text for case-insensitive factual matching.

    Example:

        "MP3, WAV"
        ->
        "mp3 wav"
    """

    return re.sub(
        r"\s+",
        " ",
        text.lower(),
    ).strip()


def contains_fact(
    text: str,
    fact: str,
) -> bool:
    """
    Check whether a factual term exists as a word/token.

    This avoids false positives such as:

        "wav" matching inside another word.
    """

    normalized_text = normalize_text(text)
    normalized_fact = normalize_text(fact)

    pattern = rf"\b{re.escape(normalized_fact)}\b"

    return bool(
        re.search(
            pattern,
            normalized_text,
        )
    )


def get_missing_facts(
    answer: str,
    expected_facts: set[str],
) -> list[str]:
    """
    Return expected facts that are missing
    from the generated answer.
    """

    return sorted(
        fact
        for fact in expected_facts
        if not contains_fact(
            answer,
            fact,
        )
    )


def get_present_facts(
    answer: str,
    expected_facts: set[str],
) -> list[str]:
    """
    Return expected facts that are present
    in the generated answer.
    """

    return sorted(
        fact
        for fact in expected_facts
        if contains_fact(
            answer,
            fact,
        )
    )


def get_wrong_facts(
    answer: str,
    known_wrong_facts: set[str],
) -> list[str]:
    """
    Return known unsupported/wrong facts appearing
    in the generated answer.
    """

    return sorted(
        fact
        for fact in known_wrong_facts
        if contains_fact(
            answer,
            fact,
        )
    )


def print_retrieved_documents(
    documents: list[dict],
) -> None:
    """
    Print the exact documents returned by the retriever.

    This is important for diagnosing whether an answer
    failure comes from retrieval or generation.
    """

    print(
        "\n"
        "============================================================\n"
        "RETRIEVED DOCUMENTS\n"
        "============================================================"
    )

    if not documents:
        print("\nNo documents were retrieved.")

    for index, document in enumerate(
        documents,
        start=1,
    ):
        print(
            f"\n"
            f"{index}. Chunk ID: "
            f"{document.get('chunk_id')}\n"
            f"   Retrieval score: "
            f"{document.get('score')}\n"
            f"   Metadata: "
            f"{document.get('metadata')}\n"
            f"   Text:\n"
            f"{document.get('text')}"
        )

    print(
        "\n"
        "============================================================"
    )


def print_answer_evaluation(
    *,
    answer: str,
    expected_facts: set[str],
    present_facts: list[str],
    missing_facts: list[str],
    wrong_facts: list[str],
) -> None:
    """
    Print a human-readable answer evaluation report.
    """

    print(
        "\n"
        "============================================================\n"
        "ANSWER CORRECTNESS EVALUATION\n"
        "============================================================\n"
        f"Expected facts: {sorted(expected_facts)}\n"
        f"Present facts:  {present_facts}\n"
        f"Missing facts:  {missing_facts}\n"
        f"Wrong facts:    {wrong_facts}\n"
        "\n"
        f"Answer:\n{answer}\n"
        "============================================================"
    )


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def correctness_conversation_id() -> str:
    """
    Provide a unique conversation ID for correctness tests.

    A unique ID prevents previous test conversations from
    affecting the current evaluation.
    """

    import uuid

    return (
        "evaluation-answer-correctness-"
        f"{uuid.uuid4().hex}"
    )


# ============================================================
# Test 1
# ============================================================


@pytest.mark.asyncio
async def test_retrieved_context_contains_expected_facts():
    """
    Verify that the retrieved context actually contains
    the facts required by the correctness evaluation.

    This test separates:

        retrieval failure

    from:

        generation failure.

    If MP3 is missing here, the problem is retrieval/context
    recall rather than answer generation.
    """

    documents = await rag_retriever.retrieve(
        QUERY
    )

    assert documents, (
        "Retriever returned no documents."
    )

    print_retrieved_documents(
        documents
    )

    retrieved_context = "\n".join(
        str(document.get("text", ""))
        for document in documents
    )

    missing_facts = get_missing_facts(
        retrieved_context,
        EXPECTED_FACTS,
    )

    present_facts = get_present_facts(
        retrieved_context,
        EXPECTED_FACTS,
    )

    print(
        "\n"
        "============================================================\n"
        "RETRIEVED FACT CHECK\n"
        "============================================================\n"
        f"Expected facts: {sorted(EXPECTED_FACTS)}\n"
        f"Present facts:  {present_facts}\n"
        f"Missing facts:  {missing_facts}\n"
        "============================================================"
    )

    assert not missing_facts, (
        "Retriever failed to return all expected facts.\n"
        f"Missing facts: {missing_facts}\n"
        f"Expected facts: {sorted(EXPECTED_FACTS)}\n\n"
        "Inspect the retrieved documents above."
    )


# ============================================================
# Test 2
# ============================================================


@pytest.mark.asyncio
async def test_answer_contains_all_expected_facts(
    correctness_conversation_id: str,
):
    """
    Verify that the generated answer contains every
    expected factual element.

    Expected answer facts:

        - MP3
        - WAV

    This test intentionally fails if the model omits
    one of the expected facts.
    """

    # --------------------------------------------------------
    # Retrieve context first for diagnostic purposes.
    # --------------------------------------------------------

    documents = await rag_retriever.retrieve(
        QUERY
    )

    assert documents, (
        "Retriever returned no documents."
    )

    print_retrieved_documents(
        documents
    )

    # --------------------------------------------------------
    # Generate answer.
    # --------------------------------------------------------

    answer = await rag_pipeline.run(
        conversation_id=correctness_conversation_id,
        message=QUERY,
    )

    assert answer, (
        "RAG pipeline returned an empty answer."
    )

    # --------------------------------------------------------
    # Evaluate expected facts.
    # --------------------------------------------------------

    present_facts = get_present_facts(
        answer,
        EXPECTED_FACTS,
    )

    missing_facts = get_missing_facts(
        answer,
        EXPECTED_FACTS,
    )

    wrong_facts = get_wrong_facts(
        answer,
        KNOWN_WRONG_FACTS,
    )

    print_answer_evaluation(
        answer=answer,
        expected_facts=EXPECTED_FACTS,
        present_facts=present_facts,
        missing_facts=missing_facts,
        wrong_facts=wrong_facts,
    )

    # --------------------------------------------------------
    # Correctness assertions.
    # --------------------------------------------------------

    assert not missing_facts, (
        "Generated answer is missing expected facts:\n"
        f"{missing_facts}\n\n"
        f"Answer:\n{answer}"
    )


# ============================================================
# Test 3
# ============================================================


@pytest.mark.asyncio
async def test_answer_does_not_contain_known_wrong_facts(
    correctness_conversation_id: str,
):
    """
    Verify that the generated answer does not introduce
    known unsupported audio formats.

    This is a negative correctness test.

    Example invalid behavior:

        "The system supports MP3, WAV, FLAC and AAC."

    if only MP3 and WAV are supported by the evaluation
    knowledge.
    """

    answer = await rag_pipeline.run(
        conversation_id=correctness_conversation_id,
        message=QUERY,
    )

    assert answer, (
        "RAG pipeline returned an empty answer."
    )

    wrong_facts = get_wrong_facts(
        answer,
        KNOWN_WRONG_FACTS,
    )

    print(
        "\n"
        "============================================================\n"
        "NEGATIVE CORRECTNESS TEST\n"
        "============================================================\n"
        f"Known wrong facts: "
        f"{sorted(KNOWN_WRONG_FACTS)}\n"
        f"Detected wrong facts: "
        f"{wrong_facts}\n"
        f"\nAnswer:\n{answer}\n"
        "============================================================"
    )

    assert not wrong_facts, (
        "Generated answer contains known unsupported facts:\n"
        f"{wrong_facts}\n\n"
        f"Answer:\n{answer}"
    )


# ============================================================
# Test 4
# ============================================================


@pytest.mark.asyncio
async def test_answer_is_not_empty(
    correctness_conversation_id: str,
):
    """
    Basic answer-quality guard.

    The RAG pipeline must return a non-empty answer for
    a supported question.
    """

    answer = await rag_pipeline.run(
        conversation_id=correctness_conversation_id,
        message=QUERY,
    )

    assert answer is not None

    assert answer.strip(), (
        "RAG pipeline returned an empty answer."
    )


# ============================================================
# Test 5
# ============================================================


@pytest.mark.asyncio
async def test_answer_contains_supported_information(
    correctness_conversation_id: str,
):
    """
    Verify that the generated answer contains at least
    one fact supported by the expected knowledge.

    This provides a less strict correctness check than
    test_answer_contains_all_expected_facts().
    """

    answer = await rag_pipeline.run(
        conversation_id=correctness_conversation_id,
        message=QUERY,
    )

    assert answer, (
        "RAG pipeline returned an empty answer."
    )

    present_facts = get_present_facts(
        answer,
        EXPECTED_FACTS,
    )

    print(
        "\n"
        "============================================================\n"
        "SUPPORTED INFORMATION CHECK\n"
        "============================================================\n"
        f"Expected facts: {sorted(EXPECTED_FACTS)}\n"
        f"Detected facts: {present_facts}\n"
        f"\nAnswer:\n{answer}\n"
        "============================================================"
    )

    assert present_facts, (
        "Generated answer contains none of the expected "
        "supported facts.\n\n"
        f"Expected facts: {sorted(EXPECTED_FACTS)}\n"
        f"Answer:\n{answer}"
    )