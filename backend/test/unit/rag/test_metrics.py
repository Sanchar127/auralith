from app.services.rag.evaluation.metrics import (
    mean_reciprocal_rank,
    recall_at_k,
    reciprocal_rank,
)


def test_recall_at_k():

    retrieved = [
        "a",
        "b",
        "c",
        "d",
        "e",
    ]

    relevant = {
        "c",
        "e",
    }

    result = recall_at_k(
        retrieved,
        relevant,
        5,
    )

    assert result == 1.0


def test_recall_at_k_partial():

    retrieved = [
        "a",
        "b",
        "c",
    ]

    relevant = {
        "c",
        "d",
    }

    result = recall_at_k(
        retrieved,
        relevant,
        3,
    )

    assert result == 0.5


def test_recall_at_k_zero():

    retrieved = [
        "a",
        "b",
    ]

    relevant = {
        "c",
    }

    result = recall_at_k(
        retrieved,
        relevant,
        2,
    )

    assert result == 0.0


def test_reciprocal_rank_first():

    retrieved = [
        "correct",
        "wrong",
    ]

    relevant = {
        "correct",
    }

    assert (
        reciprocal_rank(
            retrieved,
            relevant,
        )
        == 1.0
    )


def test_reciprocal_rank_second():

    retrieved = [
        "wrong",
        "correct",
    ]

    relevant = {
        "correct",
    }

    assert (
        reciprocal_rank(
            retrieved,
            relevant,
        )
        == 0.5
    )


def test_reciprocal_rank_not_found():

    retrieved = [
        "a",
        "b",
    ]

    relevant = {
        "c",
    }

    assert (
        reciprocal_rank(
            retrieved,
            relevant,
        )
        == 0.0
    )


def test_mean_reciprocal_rank():

    scores = [
        1.0,
        0.5,
        0.0,
    ]

    assert (
        mean_reciprocal_rank(scores)
        == 0.5
    )