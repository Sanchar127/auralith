from __future__ import annotations


def recall_at_k(
    retrieved_ids: list[str],
    relevant_ids: set[str],
    k: int,
) -> float:
    """
    Calculate Recall@K.

    Recall@K =
        number of relevant documents retrieved in top K
        /
        total number of relevant documents
    """

    if not relevant_ids:
        return 0.0

    retrieved = set(retrieved_ids[:k])

    relevant_retrieved = retrieved & relevant_ids

    return len(relevant_retrieved) / len(relevant_ids)


def reciprocal_rank(
    retrieved_ids: list[str],
    relevant_ids: set[str],
) -> float:
    """
    Calculate reciprocal rank.

    If the first relevant document is rank 1:
        RR = 1

    If rank 2:
        RR = 1 / 2

    If no relevant document is found:
        RR = 0
    """

    for rank, chunk_id in enumerate(
        retrieved_ids,
        start=1,
    ):
        if chunk_id in relevant_ids:
            return 1.0 / rank

    return 0.0


def mean_reciprocal_rank(
    rankings: list[float],
) -> float:
    """
    Calculate Mean Reciprocal Rank.
    """

    if not rankings:
        return 0.0

    return sum(rankings) / len(rankings)