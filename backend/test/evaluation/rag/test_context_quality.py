from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.services.rag.retriever import rag_retriever
from app.services.rag.vector_store import vector_store


# ==========================================================
# Paths
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent

DATASET_PATH = BASE_DIR / "dataset.json"


# ==========================================================
# Qdrant fixture
# ==========================================================


@pytest.fixture
async def qdrant_connection():
    """
    Connect to the real Qdrant service.

    This is an evaluation test, so we intentionally use
    the real vector database instead of mocking it.
    """

    await vector_store.connect()

    try:
        await vector_store.initialize()

        yield

    finally:
        await vector_store.close()


# ==========================================================
# Dataset helpers
# ==========================================================


def load_dataset() -> list[dict[str, Any]]:
    """
    Load the golden RAG evaluation dataset.
    """

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}"
        )

    with DATASET_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "dataset.json must contain a JSON list."
        )

    return data


def get_query(
    item: dict[str, Any],
) -> str:
    """
    Extract the query from a dataset item.
    """

    query = item.get("query")

    if not isinstance(query, str):
        raise ValueError(
            "Dataset item must contain a string "
            "'query' field."
        )

    query = query.strip()

    if not query:
        raise ValueError(
            "Dataset query cannot be empty."
        )

    return query


def get_relevant_chunk_ids(
    item: dict[str, Any],
) -> set[str]:
    """
    Extract the expected relevant chunk IDs.
    """

    chunk_ids = item.get(
        "relevant_chunk_ids",
        [],
    )

    if not isinstance(chunk_ids, list):
        raise ValueError(
            "'relevant_chunk_ids' must be a list."
        )

    return {
        str(chunk_id)
        for chunk_id in chunk_ids
    }


# ==========================================================
# Metric helpers
# ==========================================================


def calculate_context_precision(
    retrieved_ids: list[str],
    relevant_ids: set[str],
) -> float:
    """
    Calculate context precision.

    Precision:

        relevant retrieved chunks
        --------------------------
        all retrieved chunks
    """

    if not retrieved_ids:
        return 0.0

    relevant_count = sum(
        chunk_id in relevant_ids
        for chunk_id in retrieved_ids
    )

    return relevant_count / len(retrieved_ids)


def calculate_context_recall(
    retrieved_ids: list[str],
    relevant_ids: set[str],
) -> float:
    """
    Calculate context recall.

    Recall:

        relevant retrieved chunks
        --------------------------
        all expected relevant chunks
    """

    if not relevant_ids:
        return 1.0

    retrieved_set = set(retrieved_ids)

    relevant_retrieved = (
        retrieved_set & relevant_ids
    )

    return (
        len(relevant_retrieved)
        / len(relevant_ids)
    )


def calculate_duplicate_ratio(
    retrieved_ids: list[str],
) -> float:
    """
    Calculate the ratio of duplicate chunks.

    0.0 = no duplicates
    1.0 = everything duplicated
    """

    if not retrieved_ids:
        return 0.0

    unique_ids = set(retrieved_ids)

    duplicate_count = (
        len(retrieved_ids)
        - len(unique_ids)
    )

    return duplicate_count / len(
        retrieved_ids
    )


def calculate_context_relevance(
    documents: list[dict[str, Any]],
) -> float:
    """
    Calculate average retrieval relevance.

    The retriever already provides a Qdrant similarity
    score, so we use the average score as the deterministic
    context relevance metric.
    """

    if not documents:
        return 0.0

    scores = [
        float(document["score"])
        for document in documents
    ]

    return sum(scores) / len(scores)


def calculate_context_ordering(
    retrieved_ids: list[str],
    relevant_ids: set[str],
) -> float:
    """
    Measure whether relevant chunks appear near the top.

    A score of:

        1.0 = relevant chunks appear at the top
        0.0 = relevant chunks are at the bottom

    If no relevant chunks are retrieved, the score is 0.
    """

    if not retrieved_ids:
        return 0.0

    if not relevant_ids:
        return 1.0

    relevant_positions = [
        index
        for index, chunk_id in enumerate(
            retrieved_ids
        )
        if chunk_id in relevant_ids
    ]

    if not relevant_positions:
        return 0.0

    average_position = (
        sum(relevant_positions)
        / len(relevant_positions)
    )

    max_position = max(
        len(retrieved_ids) - 1,
        1,
    )

    return max(
        0.0,
        1.0
        - (
            average_position
            / max_position
        ),
    )


# ==========================================================
# Utility
# ==========================================================


def get_retrieved_chunk_ids(
    documents: list[dict[str, Any]],
) -> list[str]:
    """
    Extract chunk IDs from normalized retriever
    documents.
    """

    return [
        str(document["chunk_id"])
        for document in documents
    ]


# ==========================================================
# 1. Overall context quality
# ==========================================================


@pytest.mark.asyncio
async def test_context_quality(
    qdrant_connection,
):
    """
    Evaluate overall RAG context quality against
    the golden dataset.

    Metrics:

        - Context precision
        - Context recall
        - Context relevance
        - Duplicate ratio
        - Context ordering
    """

    dataset = load_dataset()

    assert dataset, (
        "Golden dataset is empty."
    )

    precision_scores: list[float] = []
    recall_scores: list[float] = []
    relevance_scores: list[float] = []
    duplicate_scores: list[float] = []
    ordering_scores: list[float] = []

    evaluated_cases = 0

    print()
    print("=" * 70)
    print("RAG CONTEXT QUALITY EVALUATION")
    print("=" * 70)

    for item in dataset:
        query = get_query(item)

        relevant_ids = (
            get_relevant_chunk_ids(item)
        )

        assert relevant_ids, (
            f"No relevant chunk IDs configured "
            f"for query: {query!r}"
        )

        documents = (
            await rag_retriever.retrieve(
                query
            )
        )

        retrieved_ids = (
            get_retrieved_chunk_ids(
                documents
            )
        )

        precision = calculate_context_precision(
            retrieved_ids,
            relevant_ids,
        )

        recall = calculate_context_recall(
            retrieved_ids,
            relevant_ids,
        )

        relevance = calculate_context_relevance(
            documents
        )

        duplicates = calculate_duplicate_ratio(
            retrieved_ids
        )

        ordering = calculate_context_ordering(
            retrieved_ids,
            relevant_ids,
        )

        precision_scores.append(precision)
        recall_scores.append(recall)
        relevance_scores.append(relevance)
        duplicate_scores.append(duplicates)
        ordering_scores.append(ordering)

        evaluated_cases += 1

        print()
        print(f"Query: {query}")
        print(
            f"Expected chunks: "
            f"{sorted(relevant_ids)}"
        )
        print(
            f"Retrieved chunks: "
            f"{retrieved_ids}"
        )
        print(
            f"Precision: {precision:.4f}"
        )
        print(
            f"Recall: {recall:.4f}"
        )
        print(
            f"Relevance: {relevance:.4f}"
        )
        print(
            f"Duplicate ratio: "
            f"{duplicates:.4f}"
        )
        print(
            f"Ordering: {ordering:.4f}"
        )

    assert evaluated_cases > 0

    average_precision = (
        sum(precision_scores)
        / len(precision_scores)
    )

    average_recall = (
        sum(recall_scores)
        / len(recall_scores)
    )

    average_relevance = (
        sum(relevance_scores)
        / len(relevance_scores)
    )

    average_duplicates = (
        sum(duplicate_scores)
        / len(duplicate_scores)
    )

    average_ordering = (
        sum(ordering_scores)
        / len(ordering_scores)
    )

    print()
    print("-" * 70)
    print(
        f"Evaluated cases:    {evaluated_cases}"
    )
    print(
        f"Context precision:  "
        f"{average_precision:.4f}"
    )
    print(
        f"Context recall:     "
        f"{average_recall:.4f}"
    )
    print(
        f"Context relevance:  "
        f"{average_relevance:.4f}"
    )
    print(
        f"Duplicate ratio:    "
        f"{average_duplicates:.4f}"
    )
    print(
        f"Context ordering:   "
        f"{average_ordering:.4f}"
    )
    print("=" * 70)

    # ------------------------------------------------------
    # Quality gates
    # ------------------------------------------------------

    assert average_precision >= 0.50, (
        "Context precision is too low: "
        f"{average_precision:.4f}"
    )

    assert average_recall >= 0.50, (
        "Context recall is too low: "
        f"{average_recall:.4f}"
    )

    assert average_relevance >= 0.35, (
        "Context relevance is too low: "
        f"{average_relevance:.4f}"
    )

    assert average_duplicates <= 0.20, (
        "Too many duplicate chunks: "
        f"{average_duplicates:.4f}"
    )


# ==========================================================
# 2. Relevant chunk retrieval
# ==========================================================


@pytest.mark.asyncio
async def test_context_contains_relevant_chunks(
    qdrant_connection,
):
    """
    Verify every golden query retrieves at least
    one expected relevant chunk.
    """

    dataset = load_dataset()

    assert dataset

    evaluated = 0

    for item in dataset:
        query = get_query(item)

        relevant_ids = (
            get_relevant_chunk_ids(item)
        )

        assert relevant_ids

        documents = (
            await rag_retriever.retrieve(
                query
            )
        )

        retrieved_ids = set(
            get_retrieved_chunk_ids(
                documents
            )
        )

        matching_ids = (
            retrieved_ids & relevant_ids
        )

        assert matching_ids, (
            "\nNo relevant chunk retrieved.\n"
            f"Query: {query}\n"
            f"Expected: {sorted(relevant_ids)}\n"
            f"Retrieved: {sorted(retrieved_ids)}"
        )

        evaluated += 1

    assert evaluated > 0


# ==========================================================
# 3. Duplicate detection
# ==========================================================


@pytest.mark.asyncio
async def test_retrieval_does_not_return_duplicate_chunks(
    qdrant_connection,
):
    """
    Verify retrieval does not return the same
    chunk multiple times.
    """

    dataset = load_dataset()

    assert dataset

    evaluated = 0

    for item in dataset:
        query = get_query(item)

        documents = (
            await rag_retriever.retrieve(
                query
            )
        )

        chunk_ids = (
            get_retrieved_chunk_ids(
                documents
            )
        )

        assert len(chunk_ids) == len(
            set(chunk_ids)
        ), (
            "\nDuplicate chunks detected.\n"
            f"Query: {query}\n"
            f"Retrieved: {chunk_ids}"
        )

        evaluated += 1

    assert evaluated > 0


# ==========================================================
# 4. Score ordering
# ==========================================================


@pytest.mark.asyncio
async def test_retrieval_results_are_ordered_by_score(
    qdrant_connection,
):
    """
    Verify Qdrant retrieval results are ordered
    from highest similarity score to lowest.
    """

    dataset = load_dataset()

    assert dataset

    evaluated = 0

    for item in dataset:
        query = get_query(item)

        documents = (
            await rag_retriever.retrieve(
                query
            )
        )

        scores = [
            float(document["score"])
            for document in documents
        ]

        assert scores == sorted(
            scores,
            reverse=True,
        ), (
            "\nRetrieval results are not ordered "
            "by descending score.\n"
            f"Query: {query}\n"
            f"Scores: {scores}"
        )

        evaluated += 1

    assert evaluated > 0