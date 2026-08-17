from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.services.rag.retriever import rag_retriever


# ==========================================================
# Paths
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent

DATASET_PATH = BASE_DIR / "dataset.json"


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
    Extract and validate the query.
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
    Extract expected relevant chunk IDs.

    An empty list means the query is unsupported
    and therefore cannot be evaluated for retrieval
    quality.
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
        if chunk_id is not None
    }


def is_evaluable(
    item: dict[str, Any],
) -> bool:
    """
    Determine whether a dataset item can be evaluated
    for retrieval quality.

    Supported and partially supported queries should
    contain relevant chunk IDs.

    Unsupported queries have no relevant chunks and
    are excluded from retrieval-quality metrics.
    """

    return bool(
        get_relevant_chunk_ids(item)
    )


# ==========================================================
# Retrieval helpers
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
        if document.get("chunk_id") is not None
    ]


def get_scores(
    documents: list[dict[str, Any]],
) -> list[float]:
    """
    Extract retrieval scores.
    """

    return [
        float(document["score"])
        for document in documents
        if document.get("score") is not None
    ]


# ==========================================================
# Metric helpers
# ==========================================================


def calculate_context_precision(
    retrieved_ids: list[str],
    relevant_ids: set[str],
) -> float:
    """
    Calculate context precision.

        relevant retrieved chunks
        --------------------------
        all retrieved chunks

    Returns 0.0 when nothing was retrieved.
    """

    if not retrieved_ids:
        return 0.0

    relevant_count = sum(
        chunk_id in relevant_ids
        for chunk_id in retrieved_ids
    )

    return (
        relevant_count
        / len(retrieved_ids)
    )


def calculate_context_recall(
    retrieved_ids: list[str],
    relevant_ids: set[str],
) -> float:
    """
    Calculate context recall.

        relevant retrieved chunks
        --------------------------
        expected relevant chunks

    An empty relevant set is not a measurable
    retrieval query and should be handled by the
    caller before calculating this metric.
    """

    if not relevant_ids:
        return 0.0

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
    Calculate duplicate ratio.

        0.0 = no duplicates
        1.0 = all retrieved entries are duplicates
    """

    if not retrieved_ids:
        return 0.0

    unique_ids = set(retrieved_ids)

    duplicate_count = (
        len(retrieved_ids)
        - len(unique_ids)
    )

    return (
        duplicate_count
        / len(retrieved_ids)
    )


def calculate_context_relevance(
    documents: list[dict[str, Any]],
) -> float:
    """
    Calculate average retrieval relevance.

    Qdrant similarity scores are used as the
    deterministic retrieval relevance signal.
    """

    scores = get_scores(documents)

    if not scores:
        return 0.0

    return sum(scores) / len(scores)


def calculate_context_ordering(
    retrieved_ids: list[str],
    relevant_ids: set[str],
) -> float:
    """
    Measure whether relevant chunks appear near
    the beginning of the retrieval result.

        1.0 = relevant chunks appear at the top
        0.0 = no relevant chunks retrieved

    Unsupported queries are not passed to this
    function.
    """

    if not retrieved_ids:
        return 0.0

    if not relevant_ids:
        return 0.0

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
# Evaluation helper
# ==========================================================


async def retrieve_documents(
    query: str,
) -> list[dict[str, Any]]:
    """
    Execute retrieval through the application's
    real RAG retriever.
    """

    return await rag_retriever.retrieve(
        query
    )


# ==========================================================
# 1. Overall context quality
# ==========================================================


@pytest.mark.asyncio
async def test_context_quality(
    rag_services,
):
    """
    Evaluate overall RAG context quality.

    Only queries containing relevant_chunk_ids
    participate in retrieval-quality metrics.

    Unsupported queries are skipped because there
    are no expected chunks against which retrieval
    quality can be measured.
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
    skipped_cases = 0

    print()
    print("=" * 70)
    print("RAG CONTEXT QUALITY EVALUATION")
    print("=" * 70)

    for item in dataset:
        query = get_query(item)

        relevant_ids = (
            get_relevant_chunk_ids(item)
        )

        # --------------------------------------------------
        # Unsupported query
        # --------------------------------------------------

        if not relevant_ids:
            skipped_cases += 1

            print()
            print(
                f"Query: {query}"
            )
            print(
                "Status: SKIPPED "
                "(no relevant_chunk_ids)"
            )

            continue

        # --------------------------------------------------
        # Retrieve
        # --------------------------------------------------

        documents = await retrieve_documents(
            query
        )

        retrieved_ids = (
            get_retrieved_chunk_ids(
                documents
            )
        )

        # --------------------------------------------------
        # Calculate metrics
        # --------------------------------------------------

        precision = (
            calculate_context_precision(
                retrieved_ids,
                relevant_ids,
            )
        )

        recall = (
            calculate_context_recall(
                retrieved_ids,
                relevant_ids,
            )
        )

        relevance = (
            calculate_context_relevance(
                documents
            )
        )

        duplicates = (
            calculate_duplicate_ratio(
                retrieved_ids
            )
        )

        ordering = (
            calculate_context_ordering(
                retrieved_ids,
                relevant_ids,
            )
        )

        # --------------------------------------------------
        # Store metrics
        # --------------------------------------------------

        precision_scores.append(
            precision
        )

        recall_scores.append(
            recall
        )

        relevance_scores.append(
            relevance
        )

        duplicate_scores.append(
            duplicates
        )

        ordering_scores.append(
            ordering
        )

        evaluated_cases += 1

        # --------------------------------------------------
        # Output
        # --------------------------------------------------

        print()
        print(
            f"Query: {query}"
        )

        print(
            "Expected chunks: "
            f"{sorted(relevant_ids)}"
        )

        print(
            "Retrieved chunks: "
            f"{retrieved_ids}"
        )

        print(
            f"Precision: "
            f"{precision:.4f}"
        )

        print(
            f"Recall: "
            f"{recall:.4f}"
        )

        print(
            f"Relevance: "
            f"{relevance:.4f}"
        )

        print(
            "Duplicate ratio: "
            f"{duplicates:.4f}"
        )

        print(
            f"Ordering: "
            f"{ordering:.4f}"
        )

    # ------------------------------------------------------
    # Dataset validation
    # ------------------------------------------------------

    assert evaluated_cases > 0, (
        "No evaluable queries found in the "
        "golden dataset. At least one query must "
        "contain relevant_chunk_ids."
    )

    # ------------------------------------------------------
    # Aggregate metrics
    # ------------------------------------------------------

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

    # ------------------------------------------------------
    # Summary
    # ------------------------------------------------------

    print()
    print("-" * 70)

    print(
        f"Total dataset queries: "
        f"{len(dataset)}"
    )

    print(
        f"Evaluated queries:     "
        f"{evaluated_cases}"
    )

    print(
        f"Skipped queries:       "
        f"{skipped_cases}"
    )

    print(
        f"Context precision:     "
        f"{average_precision:.4f}"
    )

    print(
        f"Context recall:        "
        f"{average_recall:.4f}"
    )

    print(
        f"Context relevance:     "
        f"{average_relevance:.4f}"
    )

    print(
        f"Duplicate ratio:       "
        f"{average_duplicates:.4f}"
    )

    print(
        f"Context ordering:      "
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
    rag_services,
):
    """
    Verify every evaluable golden query retrieves
    at least one expected relevant chunk.

    Unsupported queries are skipped because they
    intentionally have no relevant_chunk_ids.
    """

    dataset = load_dataset()

    assert dataset, (
        "Golden dataset is empty."
    )

    evaluated = 0
    skipped = 0

    for item in dataset:
        query = get_query(item)

        relevant_ids = (
            get_relevant_chunk_ids(item)
        )

        # --------------------------------------------------
        # Unsupported query
        # --------------------------------------------------

        if not relevant_ids:
            skipped += 1
            continue

        # --------------------------------------------------
        # Retrieve
        # --------------------------------------------------

        documents = await retrieve_documents(
            query
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

    assert evaluated > 0, (
        "No evaluable queries found."
    )

    print()
    print(
        f"Evaluated queries: {evaluated}"
    )
    print(
        f"Skipped unsupported queries: {skipped}"
    )


# ==========================================================
# 3. Duplicate detection
# ==========================================================


@pytest.mark.asyncio
async def test_retrieval_does_not_return_duplicate_chunks(
    rag_services,
):
    """
    Verify retrieval does not return the same
    chunk multiple times.

    This property can be checked for both supported
    and unsupported queries.
    """

    dataset = load_dataset()

    assert dataset, (
        "Golden dataset is empty."
    )

    evaluated = 0

    for item in dataset:
        query = get_query(item)

        documents = await retrieve_documents(
            query
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
    rag_services,
):
    """
    Verify retrieval results are ordered from
    highest similarity score to lowest similarity score.

    This property can be checked for both supported
    and unsupported queries.
    """

    dataset = load_dataset()

    assert dataset, (
        "Golden dataset is empty."
    )

    evaluated = 0

    for item in dataset:
        query = get_query(item)

        documents = await retrieve_documents(
            query
        )

        scores = get_scores(
            documents
        )

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