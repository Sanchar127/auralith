from __future__ import annotations

from typing import Any

import pytest

from app.services.rag.reranker import reranker
from app.services.rag.retriever import rag_retriever


# ==========================================================
# Test configuration
# ==========================================================

QUERY = "How does audio enhancement work?"

# These are the chunks currently known to be relevant
# for the evaluation query in your existing dataset.
RELEVANT_CHUNK_IDS = {
    "chunk-123",
    "chunk-456",
}


# ==========================================================
# Helper functions
# ==========================================================


def get_chunk_ids(
    documents: list[dict[str, Any]],
) -> list[str]:
    """
    Extract chunk IDs while preserving document ranking order.
    """

    return [
        str(document["chunk_id"])
        for document in documents
    ]


def reciprocal_rank(
    ranked_ids: list[str],
    relevant_ids: set[str],
) -> float:
    """
    Calculate Reciprocal Rank.

    Example:

        ranked:
            [chunk-999, chunk-123, chunk-456]

        relevant:
            {chunk-123, chunk-456}

        result:
            1 / 2 = 0.5

    Returns:
        0.0 when no relevant document is found.
    """

    for rank, chunk_id in enumerate(
        ranked_ids,
        start=1,
    ):
        if chunk_id in relevant_ids:
            return 1.0 / rank

    return 0.0


def precision_at_k(
    ranked_ids: list[str],
    relevant_ids: set[str],
    k: int,
) -> float:
    """
    Calculate Precision@K.

    Precision@K =
        relevant documents in top K / K

    The actual number of returned documents is used when
    fewer than K documents are available.
    """

    if k <= 0:
        return 0.0

    top_k = ranked_ids[:k]

    if not top_k:
        return 0.0

    relevant_count = sum(
        chunk_id in relevant_ids
        for chunk_id in top_k
    )

    return relevant_count / len(top_k)


def print_ranking(
    title: str,
    documents: list[dict[str, Any]],
) -> None:
    """
    Print a readable ranking for test evaluation.
    """

    print()
    print("=" * 70)
    print(title)
    print("=" * 70)

    if not documents:
        print("No documents.")
        return

    for rank, document in enumerate(
        documents,
        start=1,
    ):
        chunk_id = document.get(
            "chunk_id",
            "unknown",
        )

        retrieval_score = document.get(
            "score",
            document.get(
                "retrieval_score",
                0.0,
            ),
        )

        rerank_score = document.get(
            "rerank_score",
            None,
        )

        if rerank_score is None:
            print(
                f"{rank}. "
                f"{chunk_id} | "
                f"retrieval_score="
                f"{float(retrieval_score):.6f}"
            )
        else:
            print(
                f"{rank}. "
                f"{chunk_id} | "
                f"retrieval_score="
                f"{float(retrieval_score):.6f} | "
                f"rerank_score="
                f"{float(rerank_score):.6f}"
            )

    print("=" * 70)


# ==========================================================
# Test 1
# ==========================================================


@pytest.mark.asyncio
async def test_reranking_improves_top_k_relevance():
    """
    Compare retrieval quality before and after reranking.

    The test calculates:

        - MRR
        - Precision@3

    Reranking is required to preserve or improve the ranking.

    Important:

    If the original vector retrieval is already perfect,
    reranking cannot improve the metric further.

    In that case:

        reranked_metric == retrieval_metric

    is a valid result.
    """

    documents = await rag_retriever.retrieve(
        QUERY
    )

    assert documents, (
        "Retriever returned no documents. "
        "Cannot evaluate reranking."
    )

    # ------------------------------------------------------
    # Original retrieval ranking
    # ------------------------------------------------------

    retrieval_ids = get_chunk_ids(
        documents
    )

    # ------------------------------------------------------
    # Reranking
    # ------------------------------------------------------

    reranked_documents = reranker.rerank(
        query=QUERY,
        documents=documents,
    )

    assert reranked_documents, (
        "Reranker returned no documents."
    )

    reranked_ids = get_chunk_ids(
        reranked_documents
    )

    # ------------------------------------------------------
    # Calculate MRR
    # ------------------------------------------------------

    retrieval_mrr = reciprocal_rank(
        ranked_ids=retrieval_ids,
        relevant_ids=RELEVANT_CHUNK_IDS,
    )

    reranked_mrr = reciprocal_rank(
        ranked_ids=reranked_ids,
        relevant_ids=RELEVANT_CHUNK_IDS,
    )

    # ------------------------------------------------------
    # Calculate Precision@3
    # ------------------------------------------------------

    retrieval_precision_at_3 = precision_at_k(
        ranked_ids=retrieval_ids,
        relevant_ids=RELEVANT_CHUNK_IDS,
        k=3,
    )

    reranked_precision_at_3 = precision_at_k(
        ranked_ids=reranked_ids,
        relevant_ids=RELEVANT_CHUNK_IDS,
        k=3,
    )

    # ------------------------------------------------------
    # Evaluation output
    # ------------------------------------------------------

    print()
    print("RAG RERANKING QUALITY EVALUATION")
    print("-" * 70)
    print(f"Query: {QUERY}")
    print()
    print(
        f"Original retrieval IDs: "
        f"{retrieval_ids}"
    )
    print(
        f"Reranked IDs: "
        f"{reranked_ids}"
    )
    print()
    print(
        f"Original MRR: "
        f"{retrieval_mrr:.4f}"
    )
    print(
        f"Reranked MRR: "
        f"{reranked_mrr:.4f}"
    )
    print()
    print(
        f"Original Precision@3: "
        f"{retrieval_precision_at_3:.4f}"
    )
    print(
        f"Reranked Precision@3: "
        f"{reranked_precision_at_3:.4f}"
    )
    print("-" * 70)

    # ------------------------------------------------------
    # Quality must not decrease
    # ------------------------------------------------------

    assert reranked_mrr >= retrieval_mrr, (
        "Reranking reduced MRR.\n"
        f"Before: {retrieval_mrr:.4f}\n"
        f"After: {reranked_mrr:.4f}"
    )

    assert (
        reranked_precision_at_3
        >= retrieval_precision_at_3
    ), (
        "Reranking reduced Precision@3.\n"
        f"Before: {retrieval_precision_at_3:.4f}\n"
        f"After: {reranked_precision_at_3:.4f}"
    )


# ==========================================================
# Test 2
# ==========================================================


@pytest.mark.asyncio
async def test_compare_retrieval_before_after_reranking():
    """
    Compare the exact document ordering before and after
    reranking.

    This test does not require the ordering to change.

    A reranker is allowed to keep the same ranking when the
    original retrieval was already correct.
    """

    documents = await rag_retriever.retrieve(
        QUERY
    )

    assert documents, (
        "Retriever returned no documents."
    )

    reranked_documents = reranker.rerank(
        query=QUERY,
        documents=documents,
    )

    assert reranked_documents, (
        "Reranker returned no documents."
    )

    # ------------------------------------------------------
    # Print both rankings
    # ------------------------------------------------------

    print_ranking(
        "BEFORE RERANKING",
        documents,
    )

    print_ranking(
        "AFTER RERANKING",
        reranked_documents,
    )

    # ------------------------------------------------------
    # IDs
    # ------------------------------------------------------

    original_ids = get_chunk_ids(
        documents
    )

    reranked_ids = get_chunk_ids(
        reranked_documents
    )

    # ------------------------------------------------------
    # Reranking must not create/remove documents
    # ------------------------------------------------------

    assert set(reranked_ids) == set(
        original_ids
    ), (
        "Reranker changed the document set.\n"
        f"Original: {original_ids}\n"
        f"Reranked: {reranked_ids}"
    )


# ==========================================================
# Test 3
# ==========================================================


@pytest.mark.asyncio
async def test_reranking_scores_are_descending():
    """
    Verify that reranked documents are ordered by their
    reranker score in descending order.
    """

    documents = await rag_retriever.retrieve(
        QUERY
    )

    assert documents

    reranked_documents = reranker.rerank(
        query=QUERY,
        documents=documents,
    )

    assert reranked_documents

    # ------------------------------------------------------
    # Extract reranker scores
    # ------------------------------------------------------

    scores = [
        float(document["rerank_score"])
        for document in reranked_documents
    ]

    print()
    print("RERANKER SCORES")
    print("-" * 70)

    for rank, document in enumerate(
        reranked_documents,
        start=1,
    ):
        print(
            f"{rank}. "
            f"{document['chunk_id']} "
            f"score="
            f"{float(document['rerank_score']):.6f}"
        )

    print("-" * 70)

    # ------------------------------------------------------
    # Verify descending order
    # ------------------------------------------------------

    assert scores == sorted(
        scores,
        reverse=True,
    ), (
        "Reranked documents are not ordered "
        "by descending reranker score."
    )


# ==========================================================
# Test 4
# ==========================================================


@pytest.mark.asyncio
async def test_reranking_preserves_document_metadata():
    """
    Verify that reranking preserves all important information
    produced by the existing retriever.

    The reranker may add fields, but it must not destroy:

        - chunk_id
        - text
        - metadata
        - original retrieval score
    """

    documents = await rag_retriever.retrieve(
        QUERY
    )

    assert documents

    reranked_documents = reranker.rerank(
        query=QUERY,
        documents=documents,
    )

    assert reranked_documents

    # ------------------------------------------------------
    # Create lookup for original documents
    # ------------------------------------------------------

    original_by_id = {
        str(document["chunk_id"]): document
        for document in documents
    }

    # ------------------------------------------------------
    # Validate reranked documents
    # ------------------------------------------------------

    for reranked_document in reranked_documents:

        chunk_id = str(
            reranked_document["chunk_id"]
        )

        assert chunk_id in original_by_id, (
            f"Reranker returned unknown chunk: "
            f"{chunk_id}"
        )

        original_document = (
            original_by_id[chunk_id]
        )

        # --------------------------------------------------
        # Original fields must remain unchanged
        # --------------------------------------------------

        assert (
            reranked_document["text"]
            == original_document["text"]
        )

        assert (
            reranked_document["metadata"]
            == original_document["metadata"]
        )

        # --------------------------------------------------
        # Reranker must preserve retrieval score
        # --------------------------------------------------

        assert (
            float(
                reranked_document[
                    "retrieval_score"
                ]
            )
            == float(
                original_document["score"]
            )
        )

        # --------------------------------------------------
        # Reranker must add its own score
        # --------------------------------------------------

        assert "rerank_score" in (
            reranked_document
        )

        assert isinstance(
            reranked_document[
                "rerank_score"
            ],
            float,
        )


# ==========================================================
# Test 5
# ==========================================================


@pytest.mark.asyncio
async def test_reranking_does_not_create_fabricated_chunks():
    """
    Verify that reranking only reorders documents returned
    by the existing retriever.

    It must never fabricate a new chunk ID.
    """

    documents = await rag_retriever.retrieve(
        QUERY
    )

    assert documents

    original_ids = {
        str(document["chunk_id"])
        for document in documents
    }

    reranked_documents = reranker.rerank(
        query=QUERY,
        documents=documents,
    )

    assert reranked_documents

    reranked_ids = {
        str(document["chunk_id"])
        for document in reranked_documents
    }

    print()
    print(
        f"Original chunk IDs: "
        f"{sorted(original_ids)}"
    )
    print(
        f"Reranked chunk IDs: "
        f"{sorted(reranked_ids)}"
    )

    assert reranked_ids == original_ids, (
        "Reranker fabricated, removed, or duplicated "
        "chunk IDs."
    )


# ==========================================================
# Test 6
# ==========================================================


@pytest.mark.asyncio
async def test_reranking_top_k_contains_relevant_chunks():
    """
    Verify that relevant chunks remain available in the
    reranked top-K results.

    This test uses top_k=2.
    """

    documents = await rag_retriever.retrieve(
        QUERY
    )

    assert documents

    reranked_documents = reranker.rerank(
        query=QUERY,
        documents=documents,
        top_k=2,
    )

    assert reranked_documents

    assert len(
        reranked_documents
    ) <= 2

    reranked_top_k_ids = {
        str(document["chunk_id"])
        for document in reranked_documents
    }

    relevant_in_top_k = (
        reranked_top_k_ids
        & RELEVANT_CHUNK_IDS
    )

    print()
    print(
        f"Reranked Top-K IDs: "
        f"{sorted(reranked_top_k_ids)}"
    )
    print(
        f"Relevant IDs in Top-K: "
        f"{sorted(relevant_in_top_k)}"
    )

    assert relevant_in_top_k, (
        "No known relevant chunk was present "
        "in the reranked Top-K."
    )