
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.rag.evaluation.dataset import load_dataset
from app.services.rag.evaluation.evaluator import RetrievalEvaluator
from app.services.rag.retriever import RAGRetriever
from app.services.rag.vector_store import vector_store


REPORT_PATH = Path(
    "test/evaluation/rag/reports/retrieval_quality.json"
)


@pytest.mark.asyncio
async def test_retrieval_evaluation():
    """
    Evaluate RAG retrieval quality and generate a JSON report.

    This evaluation verifies:

        1. Qdrant is reachable.
        2. The configured collection is initialized.
        3. The evaluation dataset is loaded.
        4. Semantic retrieval is executed.
        5. Recall@K and MRR are calculated.
        6. A detailed JSON report is generated.
        7. Minimum retrieval-quality thresholds are satisfied.
    """

    # ---------------------------------------------------------
    # Connect to Qdrant
    # ---------------------------------------------------------

    await vector_store.connect()

    try:
        await vector_store.initialize()

        # -----------------------------------------------------
        # Load evaluation dataset
        # -----------------------------------------------------

        dataset = load_dataset(
            "test/evaluation/rag/dataset.json"
        )

        assert dataset, (
            "RAG evaluation dataset is empty."
        )

        # -----------------------------------------------------
        # Create retriever
        # -----------------------------------------------------

        retriever = RAGRetriever(
            top_k=10,
            score_threshold=0.35,
        )

        # -----------------------------------------------------
        # Create evaluator
        # -----------------------------------------------------

        evaluator = RetrievalEvaluator(
            retriever=retriever,
        )

        # -----------------------------------------------------
        # Run evaluation
        # -----------------------------------------------------

        metrics = await evaluator.evaluate(
            dataset
        )

        # -----------------------------------------------------
        # Build report
        # -----------------------------------------------------

        report = {
            "total_queries": metrics.total_queries,
            "recall_at_1": metrics.recall_at_1,
            "recall_at_3": metrics.recall_at_3,
            "recall_at_5": metrics.recall_at_5,
            "recall_at_10": metrics.recall_at_10,
            "mrr": metrics.mrr,
            "queries": [
                {
                    "query": result.query,
                    "retrieved_ids": result.retrieved_ids,
                    "relevant_ids": sorted(
                        result.relevant_ids
                    ),
                    "recall_at_1": result.recall_at_1,
                    "recall_at_3": result.recall_at_3,
                    "recall_at_5": result.recall_at_5,
                    "recall_at_10": result.recall_at_10,
                    "reciprocal_rank": (
                        result.reciprocal_rank
                    ),
                }
                for result in metrics.query_results
            ],
        }

        # -----------------------------------------------------
        # Write report
        # -----------------------------------------------------

        REPORT_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        REPORT_PATH.write_text(
            json.dumps(
                report,
                indent=2,
            ),
            encoding="utf-8",
        )

        # -----------------------------------------------------
        # Display evaluation results
        # -----------------------------------------------------

        print()
        print("=" * 60)
        print("RAG RETRIEVAL EVALUATION")
        print("=" * 60)

        print(
            f"Queries:    {metrics.total_queries}"
        )

        print(
            f"Recall@1:   {metrics.recall_at_1:.3f}"
        )

        print(
            f"Recall@3:   {metrics.recall_at_3:.3f}"
        )

        print(
            f"Recall@5:   {metrics.recall_at_5:.3f}"
        )

        print(
            f"Recall@10:  {metrics.recall_at_10:.3f}"
        )

        print(
            f"MRR:        {metrics.mrr:.3f}"
        )

        print("=" * 60)

        print(
            f"Report written to: {REPORT_PATH}"
        )

        # -----------------------------------------------------
        # Quality thresholds
        # -----------------------------------------------------

        assert metrics.recall_at_5 >= 0.80, (
            f"Recall@5 too low: "
            f"{metrics.recall_at_5:.3f}"
        )

        assert metrics.recall_at_10 >= 0.90, (
            f"Recall@10 too low: "
            f"{metrics.recall_at_10:.3f}"
        )

        assert metrics.mrr >= 0.70, (
            f"MRR too low: "
            f"{metrics.mrr:.3f}"
        )

    finally:
        # -----------------------------------------------------
        # Always close Qdrant
        # -----------------------------------------------------

        await vector_store.close()

