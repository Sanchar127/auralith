from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.services.rag.pipeline import rag_pipeline
from app.services.rag.retriever import rag_retriever


# ==========================================================
# Regression configuration
# ==========================================================

MIN_CONTEXT_RELEVANCE = 0.50
MIN_ANSWER_RELEVANCE = 0.50
MIN_FAITHFULNESS = 0.50
MIN_SUPPORTED_ANSWER_RATE = 0.50


# ==========================================================
# Evaluation dataset
# ==========================================================

@dataclass(frozen=True)
class RegressionCase:
    query: str
    expected_facts: tuple[str, ...]
    expected_answerable: bool


REGRESSION_DATASET = (
    RegressionCase(
        query="What audio formats are supported?",
        expected_facts=("wav", "mp3"),
        expected_answerable=True,
    ),
    RegressionCase(
        query="How does audio enhancement work?",
        expected_facts=(
            "noise reduction",
            "filtering",
            "denoising",
        ),
        expected_answerable=True,
    ),
    RegressionCase(
        query="Who invented audio enhancement technology?",
        expected_facts=(),
        expected_answerable=False,
    ),
)


# ==========================================================
# Helpers
# ==========================================================


def normalize_text(text: str) -> str:
    """Normalize text for deterministic evaluation."""

    return " ".join(
        str(text).lower().strip().split()
    )


def extract_context(
    documents: list[dict],
) -> str:
    """Combine retrieved document text."""

    return normalize_text(
        " ".join(
            str(document.get("text", ""))
            for document in documents
        )
    )


def calculate_fact_recall(
    answer: str,
    expected_facts: tuple[str, ...],
) -> float:
    """
    Calculate the percentage of expected facts present
    in the generated answer.

    Returns:
        Value between 0.0 and 1.0.
    """

    if not expected_facts:
        return 1.0

    normalized_answer = normalize_text(answer)

    matched = sum(
        1
        for fact in expected_facts
        if fact.lower() in normalized_answer
    )

    return matched / len(expected_facts)


def calculate_context_relevance(
    documents: list[dict],
) -> float:
    """
    Estimate context quality from retrieval scores.

    The current retriever already exposes Qdrant retrieval
    scores through the `score` field.

    This is a lightweight regression metric rather than a
    semantic evaluator.
    """

    if not documents:
        return 0.0

    scores = []

    for document in documents:
        score = document.get("score")

        if score is None:
            continue

        try:
            scores.append(float(score))
        except (TypeError, ValueError):
            continue

    if not scores:
        return 0.0

    return sum(scores) / len(scores)


def contains_uncertainty_statement(
    answer: str,
) -> bool:
    """Detect explicit acknowledgement of missing knowledge."""

    normalized = normalize_text(answer)

    uncertainty_patterns = (
        "not enough information",
        "does not contain enough information",
        "available knowledge is insufficient",
        "i don't have enough information",
        "information is not available",
        "cannot determine",
        "unable to determine",
        "not provided",
        "not specified",
    )

    return any(
        pattern in normalized
        for pattern in uncertainty_patterns
    )


def answer_is_supported(
    answer: str,
    context: str,
) -> bool:
    """
    Lightweight faithfulness check.

    At least one meaningful context term should appear
    in the answer for answerable questions.
    """

    normalized_answer = normalize_text(answer)

    factual_terms = (
        "wav",
        "mp3",
        "noise reduction",
        "filtering",
        "denoising",
        "audio enhancement",
        "audio quality",
    )

    for term in factual_terms:
        if (
            term in normalized_answer
            and term in context
        ):
            return True

    return False


# ==========================================================
# Regression result
# ==========================================================


@dataclass
class RegressionResult:
    query: str
    context_score: float
    answer_fact_recall: float
    faithful: bool
    answer_relevant: bool


# ==========================================================
# Run regression evaluation
# ==========================================================


@pytest.mark.asyncio
async def test_rag_regression_baseline():
    """
    Run the complete RAG regression evaluation.

    The test verifies that the current RAG implementation
    has not dropped below the minimum quality thresholds.
    """

    results: list[RegressionResult] = []

    for index, case in enumerate(REGRESSION_DATASET):

        documents = await rag_retriever.retrieve(
            case.query
        )

        context = extract_context(
            documents
        )

        answer = await rag_pipeline.run(
            conversation_id=(
                f"evaluation-regression-{index}"
            ),
            message=case.query,
        )

        assert answer, (
            f"RAG returned an empty answer for query: "
            f"{case.query}"
        )

        # --------------------------------------------------
        # Context quality
        # --------------------------------------------------

        context_score = calculate_context_relevance(
            documents
        )

        # --------------------------------------------------
        # Answer correctness
        # --------------------------------------------------

        fact_recall = calculate_fact_recall(
            answer,
            case.expected_facts,
        )

        # --------------------------------------------------
        # Faithfulness
        # --------------------------------------------------

        if case.expected_answerable:
            faithful = answer_is_supported(
                answer,
                context,
            )
        else:
            faithful = contains_uncertainty_statement(
                answer
            )

        # --------------------------------------------------
        # Answer relevance
        # --------------------------------------------------

        if case.expected_answerable:

            answer_relevant = (
                fact_recall > 0.0
            )

        else:

            answer_relevant = (
                contains_uncertainty_statement(
                    answer
                )
            )

        result = RegressionResult(
            query=case.query,
            context_score=context_score,
            answer_fact_recall=fact_recall,
            faithful=faithful,
            answer_relevant=answer_relevant,
        )

        results.append(result)

        # --------------------------------------------------
        # Print individual result
        # --------------------------------------------------

        print(
            "\n"
            "============================================================\n"
            f"REGRESSION CASE {index + 1}\n"
            "============================================================\n"
            f"Query:\n{case.query}\n\n"
            f"Retrieved chunks:\n"
            f"{[document.get('chunk_id') for document in documents]}\n\n"
            f"Context score:\n{context_score:.4f}\n\n"
            f"Answer fact recall:\n{fact_recall:.4f}\n\n"
            f"Faithful:\n{faithful}\n\n"
            f"Answer relevant:\n{answer_relevant}\n\n"
            f"Answer:\n{answer}\n"
            "============================================================"
        )

    # ======================================================
    # Aggregate metrics
    # ======================================================

    total_cases = len(results)

    assert total_cases > 0

    average_context_score = (
        sum(
            result.context_score
            for result in results
        )
        / total_cases
    )

    average_fact_recall = (
        sum(
            result.answer_fact_recall
            for result in results
        )
        / total_cases
    )

    faithfulness_rate = (
        sum(
            1
            for result in results
            if result.faithful
        )
        / total_cases
    )

    answer_relevance_rate = (
        sum(
            1
            for result in results
            if result.answer_relevant
        )
        / total_cases
    )

    # ======================================================
    # Regression report
    # ======================================================

    print(
        "\n"
        "\n"
        "################################################################\n"
        "#                    RAG REGRESSION REPORT                    #\n"
        "################################################################\n"
        f"Cases evaluated:              {total_cases}\n"
        f"Average context score:        "
        f"{average_context_score:.4f}\n"
        f"Average fact recall:          "
        f"{average_fact_recall:.4f}\n"
        f"Faithfulness rate:            "
        f"{faithfulness_rate:.4f}\n"
        f"Answer relevance rate:        "
        f"{answer_relevance_rate:.4f}\n"
        "################################################################"
    )

    # ======================================================
    # Regression thresholds
    # ======================================================

    assert average_context_score >= MIN_CONTEXT_RELEVANCE, (
        "\nRAG regression detected: context quality dropped "
        "below the minimum threshold.\n"
        f"Current: {average_context_score:.4f}\n"
        f"Required: {MIN_CONTEXT_RELEVANCE:.4f}"
    )

    assert average_fact_recall >= MIN_ANSWER_RELEVANCE, (
        "\nRAG regression detected: answer fact recall "
        "dropped below the minimum threshold.\n"
        f"Current: {average_fact_recall:.4f}\n"
        f"Required: {MIN_ANSWER_RELEVANCE:.4f}"
    )

    assert faithfulness_rate >= MIN_FAITHFULNESS, (
        "\nRAG regression detected: faithfulness rate "
        "dropped below the minimum threshold.\n"
        f"Current: {faithfulness_rate:.4f}\n"
        f"Required: {MIN_FAITHFULNESS:.4f}"
    )

    assert answer_relevance_rate >= MIN_SUPPORTED_ANSWER_RATE, (
        "\nRAG regression detected: answer relevance rate "
        "dropped below the minimum threshold.\n"
        f"Current: {answer_relevance_rate:.4f}\n"
        f"Required: {MIN_SUPPORTED_ANSWER_RATE:.4f}"
    )