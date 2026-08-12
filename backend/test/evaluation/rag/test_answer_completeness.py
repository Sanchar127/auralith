from __future__ import annotations

import re
import uuid

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

KNOWN_UNSUPPORTED_FACTS = {
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
    Normalize text for reliable fact matching.
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
    Check whether a fact appears as a complete token.
    """

    normalized_text = normalize_text(text)
    normalized_fact = normalize_text(fact)

    return bool(
        re.search(
            rf"\b{re.escape(normalized_fact)}\b",
            normalized_text,
        )
    )


def extract_present_facts(
    answer: str,
    facts: set[str],
) -> list[str]:
    """
    Return expected facts found in the answer.
    """

    return sorted(
        fact
        for fact in facts
        if contains_fact(
            answer,
            fact,
        )
    )


def extract_missing_facts(
    answer: str,
    facts: set[str],
) -> list[str]:
    """
    Return expected facts missing from the answer.
    """

    return sorted(
        fact
        for fact in facts
        if not contains_fact(
            answer,
            fact,
        )
    )


def extract_unsupported_facts(
    answer: str,
    facts: set[str],
) -> list[str]:
    """
    Return known unsupported facts found in the answer.
    """

    return sorted(
        fact
        for fact in facts
        if contains_fact(
            answer,
            fact,
        )
    )


def print_evaluation(
    *,
    answer: str,
    present_facts: list[str],
    missing_facts: list[str],
    unsupported_facts: list[str],
) -> None:
    """
    Print a completeness evaluation report.
    """

    print(
        "\n"
        "============================================================\n"
        "ANSWER COMPLETENESS EVALUATION\n"
        "============================================================\n"
        f"Expected facts:     {sorted(EXPECTED_FACTS)}\n"
        f"Present facts:      {present_facts}\n"
        f"Missing facts:      {missing_facts}\n"
        f"Unsupported facts:  {unsupported_facts}\n"
        "\n"
        f"Answer:\n{answer}\n"
        "============================================================"
    )


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def conversation_id() -> str:
    """
    Generate an isolated conversation ID for each test.
    """

    return (
        "evaluation-answer-completeness-"
        f"{uuid.uuid4().hex}"
    )


# ============================================================
# Test 1
# ============================================================


@pytest.mark.asyncio
async def test_retrieved_context_supports_expected_answer():
    """
    Verify that the retrieved context contains the information
    required to produce a complete answer.

    This prevents a generation test from incorrectly blaming
    the LLM when retrieval itself is incomplete.
    """

    documents = await rag_retriever.retrieve(
        QUERY
    )

    assert documents, (
        "Retriever returned no documents."
    )

    retrieved_context = "\n".join(
        str(document.get("text", ""))
        for document in documents
    )

    present_facts = extract_present_facts(
        retrieved_context,
        EXPECTED_FACTS,
    )

    missing_facts = extract_missing_facts(
        retrieved_context,
        EXPECTED_FACTS,
    )

    print(
        "\n"
        "============================================================\n"
        "RETRIEVED CONTEXT COMPLETENESS\n"
        "============================================================\n"
        f"Expected facts: {sorted(EXPECTED_FACTS)}\n"
        f"Present facts:  {present_facts}\n"
        f"Missing facts:  {missing_facts}\n"
        "\n"
        f"Retrieved context:\n{retrieved_context}\n"
        "============================================================"
    )

    assert not missing_facts, (
        "Retrieved context does not contain all information "
        "required for a complete answer.\n"
        f"Missing facts: {missing_facts}"
    )


# ============================================================
# Test 2
# ============================================================


@pytest.mark.asyncio
async def test_answer_contains_all_required_information(
    conversation_id: str,
):
    """
    Verify that the generated answer contains every required
    factual element.

    Completeness means that the answer does not omit required
    supported information.
    """

    answer = await rag_pipeline.run(
        conversation_id=conversation_id,
        message=QUERY,
    )

    assert answer, (
        "RAG pipeline returned an empty answer."
    )

    present_facts = extract_present_facts(
        answer,
        EXPECTED_FACTS,
    )

    missing_facts = extract_missing_facts(
        answer,
        EXPECTED_FACTS,
    )

    unsupported_facts = extract_unsupported_facts(
        answer,
        KNOWN_UNSUPPORTED_FACTS,
    )

    print_evaluation(
        answer=answer,
        present_facts=present_facts,
        missing_facts=missing_facts,
        unsupported_facts=unsupported_facts,
    )

    assert not missing_facts, (
        "Answer is incomplete.\n"
        f"Missing expected facts: {missing_facts}\n\n"
        f"Answer:\n{answer}"
    )


# ============================================================
# Test 3
# ============================================================


@pytest.mark.asyncio
async def test_answer_does_not_add_unsupported_information(
    conversation_id: str,
):
    """
    Verify that completeness does not come at the cost of
    hallucination.

    An answer should contain all supported facts without
    adding known unsupported formats.
    """

    answer = await rag_pipeline.run(
        conversation_id=conversation_id,
        message=QUERY,
    )

    assert answer, (
        "RAG pipeline returned an empty answer."
    )

    unsupported_facts = extract_unsupported_facts(
        answer,
        KNOWN_UNSUPPORTED_FACTS,
    )

    print(
        "\n"
        "============================================================\n"
        "UNSUPPORTED INFORMATION CHECK\n"
        "============================================================\n"
        f"Known unsupported facts: "
        f"{sorted(KNOWN_UNSUPPORTED_FACTS)}\n"
        f"Detected unsupported facts: "
        f"{unsupported_facts}\n"
        f"\nAnswer:\n{answer}\n"
        "============================================================"
    )

    assert not unsupported_facts, (
        "Answer contains unsupported information.\n"
        f"Unsupported facts: {unsupported_facts}\n\n"
        f"Answer:\n{answer}"
    )


# ============================================================
# Test 4
# ============================================================


@pytest.mark.asyncio
async def test_answer_contains_at_least_one_supported_fact(
    conversation_id: str,
):
    """
    Verify that the answer actually contains information
    relevant to the retrieved knowledge.

    This is a weaker completeness check than requiring every
    expected fact.
    """

    answer = await rag_pipeline.run(
        conversation_id=conversation_id,
        message=QUERY,
    )

    assert answer, (
        "RAG pipeline returned an empty answer."
    )

    present_facts = extract_present_facts(
        answer,
        EXPECTED_FACTS,
    )

    print(
        "\n"
        "============================================================\n"
        "SUPPORTED FACT CHECK\n"
        "============================================================\n"
        f"Expected facts: {sorted(EXPECTED_FACTS)}\n"
        f"Present facts:  {present_facts}\n"
        f"\nAnswer:\n{answer}\n"
        "============================================================"
    )

    assert present_facts, (
        "Answer contains none of the expected supported "
        "information.\n\n"
        f"Answer:\n{answer}"
    )


# ============================================================
# Test 5
# ============================================================


@pytest.mark.asyncio
async def test_answer_is_not_excessively_short(
    conversation_id: str,
):
    """
    Basic completeness guard.

    The answer should provide more than an empty or trivial
    response for a supported knowledge question.

    This test intentionally uses a very conservative threshold
    so it does not enforce a particular writing style.
    """

    answer = await rag_pipeline.run(
        conversation_id=conversation_id,
        message=QUERY,
    )

    assert answer, (
        "RAG pipeline returned an empty answer."
    )

    normalized_answer = normalize_text(
        answer
    )

    assert len(normalized_answer) >= 10, (
        "Generated answer is suspiciously short and may not "
        "contain a meaningful response.\n\n"
        f"Answer:\n{answer}"
    )