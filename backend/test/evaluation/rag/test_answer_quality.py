from __future__ import annotations

import re
import uuid

import pytest

from app.services.rag.pipeline import rag_pipeline


# ============================================================
# Test configuration
# ============================================================

QUERY = "What audio formats are supported?"

EXPECTED_TERMS = {
    "mp3",
    "wav",
}

KNOWN_BAD_PATTERNS = [
    "i don't know",
    "i cannot answer",
    "as an ai language model",
    "according to my training data",
    "based on my pretrained knowledge",
]


# ============================================================
# Helpers
# ============================================================


def normalize_text(text: str) -> str:
    """
    Normalize generated text for evaluation.
    """

    return re.sub(
        r"\s+",
        " ",
        text.lower(),
    ).strip()


def contains_supported_information(
    answer: str,
) -> bool:
    """
    Verify that the answer contains at least one expected
    piece of supported information.
    """

    normalized = normalize_text(
        answer
    )

    return any(
        re.search(
            rf"\b{re.escape(term)}\b",
            normalized,
        )
        for term in EXPECTED_TERMS
    )


def find_bad_patterns(
    answer: str,
) -> list[str]:
    """
    Detect obvious low-quality or policy-breaking phrases.
    """

    normalized = normalize_text(
        answer
    )

    return [
        pattern
        for pattern in KNOWN_BAD_PATTERNS
        if pattern in normalized
    ]


def print_quality_report(
    answer: str,
    *,
    word_count: int,
    sentence_count: int,
    bad_patterns: list[str],
) -> None:
    """
    Print a human-readable quality report.
    """

    print(
        "\n"
        "============================================================\n"
        "ANSWER QUALITY EVALUATION\n"
        "============================================================\n"
        f"Word count:      {word_count}\n"
        f"Sentence count:  {sentence_count}\n"
        f"Bad patterns:    {bad_patterns}\n"
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
    Generate an isolated conversation ID.
    """

    return (
        "evaluation-answer-quality-"
        f"{uuid.uuid4().hex}"
    )


# ============================================================
# Test 1
# ============================================================


@pytest.mark.asyncio
async def test_answer_is_non_empty(
    conversation_id: str,
):
    """
    Verify that the RAG pipeline returns a meaningful
    non-empty answer.
    """

    answer = await rag_pipeline.run(
        conversation_id=conversation_id,
        message=QUERY,
    )

    assert answer is not None

    assert answer.strip(), (
        "RAG pipeline returned an empty answer."
    )


# ============================================================
# Test 2
# ============================================================


@pytest.mark.asyncio
async def test_answer_has_reasonable_length(
    conversation_id: str,
):
    """
    Verify that the generated answer is neither empty nor
    excessively short.

    The threshold is intentionally conservative so this test
    does not enforce a particular response style.
    """

    answer = await rag_pipeline.run(
        conversation_id=conversation_id,
        message=QUERY,
    )

    assert answer

    normalized = normalize_text(
        answer
    )

    word_count = len(
        normalized.split()
    )

    print(
        "\n"
        "============================================================\n"
        "ANSWER LENGTH\n"
        "============================================================\n"
        f"Word count: {word_count}\n"
        f"Answer:\n{answer}\n"
        "============================================================"
    )

    assert word_count >= 3, (
        "Answer is too short to provide a meaningful response.\n\n"
        f"Answer:\n{answer}"
    )


# ============================================================
# Test 3
# ============================================================


@pytest.mark.asyncio
async def test_answer_contains_supported_information(
    conversation_id: str,
):
    """
    Verify that the answer contains at least one piece of
    information relevant to the question.
    """

    answer = await rag_pipeline.run(
        conversation_id=conversation_id,
        message=QUERY,
    )

    assert answer

    supported = contains_supported_information(
        answer
    )

    print(
        "\n"
        "============================================================\n"
        "SUPPORTED INFORMATION\n"
        "============================================================\n"
        f"Expected terms: {sorted(EXPECTED_TERMS)}\n"
        f"Contains supported information: {supported}\n"
        f"\nAnswer:\n{answer}\n"
        "============================================================"
    )

    assert supported, (
        "Answer does not contain any expected supported "
        "information.\n\n"
        f"Answer:\n{answer}"
    )


# ============================================================
# Test 4
# ============================================================


@pytest.mark.asyncio
async def test_answer_does_not_contain_known_bad_patterns(
    conversation_id: str,
):
    """
    Verify that the answer does not contain obvious
    low-quality or inappropriate generation patterns.
    """

    answer = await rag_pipeline.run(
        conversation_id=conversation_id,
        message=QUERY,
    )

    assert answer

    bad_patterns = find_bad_patterns(
        answer
    )

    print(
        "\n"
        "============================================================\n"
        "BAD PATTERN CHECK\n"
        "============================================================\n"
        f"Detected patterns: {bad_patterns}\n"
        f"\nAnswer:\n{answer}\n"
        "============================================================"
    )

    assert not bad_patterns, (
        "Answer contains known low-quality patterns:\n"
        f"{bad_patterns}\n\n"
        f"Answer:\n{answer}"
    )


# ============================================================
# Test 5
# ============================================================


@pytest.mark.asyncio
async def test_answer_contains_complete_sentences(
    conversation_id: str,
):
    """
    Verify that the answer contains at least one sentence-like
    response rather than returning only an isolated token.
    """

    answer = await rag_pipeline.run(
        conversation_id=conversation_id,
        message=QUERY,
    )

    assert answer

    normalized = normalize_text(
        answer
    )

    sentence_count = len(
        [
            sentence
            for sentence in re.split(
                r"[.!?]+",
                normalized,
            )
            if sentence.strip()
        ]
    )

    word_count = len(
        normalized.split()
    )

    print(
        "\n"
        "============================================================\n"
        "SENTENCE QUALITY\n"
        "============================================================\n"
        f"Sentence count: {sentence_count}\n"
        f"Word count:     {word_count}\n"
        f"\nAnswer:\n{answer}\n"
        "============================================================"
    )

    assert sentence_count >= 1, (
        "Answer does not contain a complete sentence."
    )


# ============================================================
# Test 6
# ============================================================


@pytest.mark.asyncio
async def test_answer_is_not_excessively_verbose(
    conversation_id: str,
):
    """
    Verify that the answer does not become excessively long
    for a simple factual question.

    This is only a sanity check and does not enforce a strict
    writing style.
    """

    answer = await rag_pipeline.run(
        conversation_id=conversation_id,
        message=QUERY,
    )

    assert answer

    normalized = normalize_text(
        answer
    )

    word_count = len(
        normalized.split()
    )

    print(
        "\n"
        "============================================================\n"
        "VERBOSITY CHECK\n"
        "============================================================\n"
        f"Word count: {word_count}\n"
        f"\nAnswer:\n{answer}\n"
        "============================================================"
    )

    assert word_count <= 300, (
        "Answer is excessively verbose for this simple "
        "evaluation question.\n\n"
        f"Word count: {word_count}\n"
        f"Answer:\n{answer}"
    )


# ============================================================
# Test 7
# ============================================================


@pytest.mark.asyncio
async def test_answer_quality_report(
    conversation_id: str,
):
    """
    Combined answer-quality sanity check.

    This test provides a compact overall quality signal while
    keeping the individual tests above useful for diagnosing
    specific failures.
    """

    answer = await rag_pipeline.run(
        conversation_id=conversation_id,
        message=QUERY,
    )

    assert answer

    normalized = normalize_text(
        answer
    )

    word_count = len(
        normalized.split()
    )

    sentence_count = len(
        [
            sentence
            for sentence in re.split(
                r"[.!?]+",
                normalized,
            )
            if sentence.strip()
        ]
    )

    bad_patterns = find_bad_patterns(
        answer
    )

    print_quality_report(
        answer,
        word_count=word_count,
        sentence_count=sentence_count,
        bad_patterns=bad_patterns,
    )

    assert word_count >= 3
    assert sentence_count >= 1
    assert not bad_patterns
    assert contains_supported_information(
        answer
    )