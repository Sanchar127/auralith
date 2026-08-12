import json

import pytest

from app.services.rag.evaluation.dataset import load_dataset
from app.services.rag.evaluation.evaluator import RetrievalEvaluator
from app.services.rag.indexer import rag_indexer
from app.services.rag.retriever import RAGRetriever
from app.services.rag.vector_store import vector_store


@pytest.mark.asyncio
async def test_retrieval_quality():
    """
    Evaluate semantic retrieval quality against the
    RAG evaluation dataset.
    """

    await vector_store.connect()

    try:
        await vector_store.initialize()

        # ---------------------------------------------------------
        # Load evaluation queries
        # ---------------------------------------------------------

        dataset = load_dataset(
            "test/evaluation/rag/dataset.json"
        )

        assert dataset, (
            "RAG evaluation dataset is empty."
        )

        # ---------------------------------------------------------
        # Load evaluation documents
        # ---------------------------------------------------------

        with open(
            "test/evaluation/rag/documents.json",
            "r",
            encoding="utf-8",
        ) as file:
            documents = json.load(file)

        assert documents, (
            "RAG evaluation documents are empty."
        )

        # ---------------------------------------------------------
        # Index evaluation documents
        # ---------------------------------------------------------

        await rag_indexer.index_documents(
            documents
        )

        # ---------------------------------------------------------
        # Verify Qdrant contains documents
        # ---------------------------------------------------------

        client = vector_store._get_client()

        count_result = await client.count(
            collection_name=vector_store.collection,
            exact=True,
        )

        assert count_result.count > 0, (
            f"Qdrant collection "
            f"'{vector_store.collection}' contains "
            "no indexed documents."
        )

        # ---------------------------------------------------------
        # Create retriever
        # ---------------------------------------------------------

        retriever = RAGRetriever(
            top_k=10,
            score_threshold=0.35,
        )

        evaluator = RetrievalEvaluator(
            retriever=retriever,
        )

        # ---------------------------------------------------------
        # Evaluate
        # ---------------------------------------------------------

        metrics = await evaluator.evaluate(
            dataset
        )

        # ---------------------------------------------------------
        # Display results
        # ---------------------------------------------------------

        print()
        print("=" * 60)
        print("RAG RETRIEVAL QUALITY")
        print("=" * 60)

        print(
            f"Queries:   {metrics.total_queries}"
        )

        print(
            f"Recall@1:  {metrics.recall_at_1:.3f}"
        )

        print(
            f"Recall@3:  {metrics.recall_at_3:.3f}"
        )

        print(
            f"Recall@5:  {metrics.recall_at_5:.3f}"
        )

        print(
            f"Recall@10: {metrics.recall_at_10:.3f}"
        )

        print(
            f"MRR:       {metrics.mrr:.3f}"
        )

        print("=" * 60)

        # ---------------------------------------------------------
        # Quality thresholds
        # ---------------------------------------------------------

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
        await vector_store.close()