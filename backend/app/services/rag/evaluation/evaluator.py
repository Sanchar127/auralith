from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from app.services.rag.evaluation.dataset import (
    RetrievalTestCase,
)
from app.services.rag.evaluation.metrics import (
    mean_reciprocal_rank,
    recall_at_k,
    reciprocal_rank,
)
from app.services.rag.retriever import (
    RAGRetriever,
)


@dataclass
class QueryEvaluation:
    query: str

    retrieved_ids: list[str]
    relevant_ids: set[str]

    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    recall_at_10: float

    reciprocal_rank: float


@dataclass
class RetrievalMetrics:
    total_queries: int

    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    recall_at_10: float

    mrr: float

    query_results: list[QueryEvaluation]


class RetrievalEvaluator:
    """
    Evaluates the actual RAG retriever.
    """

    def __init__(
        self,
        retriever: RAGRetriever,
    ):
        self.retriever = retriever

    async def evaluate(
        self,
        dataset: list[RetrievalTestCase],
    ) -> RetrievalMetrics:

        if not dataset:
            raise ValueError(
                "Evaluation dataset cannot be empty."
            )

        query_results: list[QueryEvaluation] = []

        for test_case in dataset:

            documents = await self.retriever.retrieve(
                test_case.query
            )

            retrieved_ids = [
                document["chunk_id"]
                for document in documents
            ]

            relevant_ids = (
                test_case.relevant_chunk_ids
            )

            result = QueryEvaluation(
                query=test_case.query,

                retrieved_ids=retrieved_ids,

                relevant_ids=relevant_ids,

                recall_at_1=recall_at_k(
                    retrieved_ids,
                    relevant_ids,
                    1,
                ),

                recall_at_3=recall_at_k(
                    retrieved_ids,
                    relevant_ids,
                    3,
                ),

                recall_at_5=recall_at_k(
                    retrieved_ids,
                    relevant_ids,
                    5,
                ),

                recall_at_10=recall_at_k(
                    retrieved_ids,
                    relevant_ids,
                    10,
                ),

                reciprocal_rank=reciprocal_rank(
                    retrieved_ids,
                    relevant_ids,
                ),
            )

            query_results.append(result)

        return RetrievalMetrics(
            total_queries=len(
                query_results
            ),

            recall_at_1=mean(
                result.recall_at_1
                for result in query_results
            ),

            recall_at_3=mean(
                result.recall_at_3
                for result in query_results
            ),

            recall_at_5=mean(
                result.recall_at_5
                for result in query_results
            ),

            recall_at_10=mean(
                result.recall_at_10
                for result in query_results
            ),

            mrr=mean_reciprocal_rank(
                [
                    result.reciprocal_rank
                    for result in query_results
                ]
            ),

            query_results=query_results,
        )