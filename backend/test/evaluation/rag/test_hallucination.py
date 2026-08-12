from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from app.services.rag.pipeline import rag_pipeline
from app.services.rag.retriever import rag_retriever


# ============================================================
# Paths
# ============================================================

TEST_DIR = Path(__file__).resolve().parent

DATASET_PATH = TEST_DIR / "dataset.json"

REPORT_DIR = TEST_DIR / "reports"

REPORT_PATH = REPORT_DIR / "hallucination_report.json"


# ============================================================
# Dataset helpers
# ============================================================


def load_dataset() -> list[dict[str, Any]]:
    """
    Load the hallucination evaluation dataset.

    Expected format:

    [
        {
            "query": "...",
            "type": "unsupported",
            "relevant_chunk_ids": []
        },
        {
            "query": "...",
            "type": "supported",
            "relevant_chunk_ids": [
                "chunk-123"
            ]
        },
        {
            "query": "...",
            "type": "partial",
            "relevant_chunk_ids": [
                "chunk-456"
            ]
        }
    ]
    """

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Hallucination dataset not found: "
            f"{DATASET_PATH}"
        )

    with DATASET_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "Hallucination dataset must contain "
            "a JSON list."
        )

    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(
                f"Dataset item at index {index} "
                f"must be a JSON object."
            )

    return data


def get_query(item: dict[str, Any]) -> str:
    """
    Extract and validate the query from a dataset item.
    """

    query = item.get("query")

    if not isinstance(query, str):
        raise ValueError(
            f"Dataset item has invalid query: {item}"
        )

    query = query.strip()

    if not query:
        raise ValueError(
            f"Dataset item contains an empty query: {item}"
        )

    return query


def get_case_type(item: dict[str, Any]) -> str:
    """
    Extract and validate the hallucination case type.

    Supported types:

        supported
        unsupported
        partial
    """

    case_type = item.get("type")

    if not isinstance(case_type, str):
        raise ValueError(
            f"Dataset item has invalid type: {item}"
        )

    case_type = case_type.strip().lower()

    allowed_types = {
        "supported",
        "unsupported",
        "partial",
    }

    if case_type not in allowed_types:
        raise ValueError(
            f"Unknown hallucination case type "
            f"{case_type!r}. "
            f"Expected one of "
            f"{sorted(allowed_types)}."
        )

    return case_type


def get_relevant_chunk_ids(
    item: dict[str, Any],
) -> list[str]:
    """
    Extract expected relevant chunk IDs.
    """

    values = item.get(
        "relevant_chunk_ids",
        [],
    )

    if values is None:
        return []

    if not isinstance(values, list):
        raise ValueError(
            "relevant_chunk_ids must be a list."
        )

    return [
        str(value)
        for value in values
        if value is not None
    ]


# ============================================================
# Text normalization
# ============================================================


def normalize_text(text: str) -> str:
    """
    Normalize text for phrase matching.
    """

    return " ".join(
        text.lower().split()
    )


# ============================================================
# Uncertainty / refusal detection
# ============================================================


# ============================================================
# Answer safety detection
# ============================================================

UNCERTAINTY_PHRASES = (
    # Direct uncertainty
    "i don't know",
    "i do not know",
    "i'm not sure",
    "i am not sure",
    "not sure",
    "i cannot determine",
    "i can't determine",
    "cannot determine",
    "can't determine",
    "i cannot confirm",
    "i can't confirm",
    "cannot confirm",
    "can't confirm",

    # Missing information
    "i don't have enough information",
    "i do not have enough information",
    "not enough information",
    "insufficient information",
    "no information available",
    "information is not available",
    "information is unavailable",

    # Context limitations
    "the context does not contain",
    "the context doesn't contain",
    "the provided context does not contain",
    "the provided context doesn't contain",

    "the context does not provide",
    "the context doesn't provide",
    "the provided context does not provide",
    "the provided context doesn't provide",

    "the context does not mention",
    "the context doesn't mention",
    "the provided context does not mention",
    "the provided context doesn't mention",

    "the context does not specify",
    "the context doesn't specify",
    "the provided context does not specify",
    "the provided context doesn't specify",

    "the context does not include",
    "the context doesn't include",
    "the provided context does not include",
    "the provided context doesn't include",

    # Knowledge limitations
    "the available knowledge does not contain",
    "the available knowledge doesn't contain",
    "the available knowledge does not provide",
    "the available knowledge doesn't provide",
    "the available knowledge does not mention",
    "the available knowledge doesn't mention",
    "the available knowledge does not specify",
    "the available knowledge doesn't specify",
    "the available knowledge does not include",
    "the available knowledge doesn't include",

    # Explicit unsupported statements
    "not provided in the context",
    "not mentioned in the context",
    "not specified in the context",
    "not included in the context",

    "not provided in the available knowledge",
    "not mentioned in the available knowledge",
    "not specified in the available knowledge",
    "not included in the available knowledge",

    "unsupported by the provided context",
    "unsupported by the available context",
    "unsupported by the available information",
    "not supported by the context",
    "not supported by the available information",

    # Cannot answer
    "cannot answer from the provided context",
    "can't answer from the provided context",
    "cannot answer from the available knowledge",
    "can't answer from the available knowledge",

    # Outside knowledge boundary
    "outside the provided context",
    "outside the available knowledge",
    "beyond the provided context",
    "beyond the available knowledge",

    # Common LLM formulations
    "does not specify",
    "doesn't specify",
    "does not provide information",
    "doesn't provide information",
    "does not contain information",
    "doesn't contain information",
    "does not provide details",
    "doesn't provide details",
    "does not contain details",
    "doesn't contain details",
    "no information on",
    "no information about",
    "there is no information",
    "there isn't information",
)


def normalize_text(text: str) -> str:
    """
    Normalize text for reliable phrase matching.
    """

    if not isinstance(text, str):
        return ""

    return " ".join(text.lower().split())


def contains_uncertainty(answer: str) -> bool:
    """
    Detect whether the answer explicitly acknowledges
    that requested information is unavailable,
    unsupported, or cannot be established from
    the retrieved knowledge.
    """

    normalized = normalize_text(answer)

    if not normalized:
        return False

    return any(
        phrase in normalized
        for phrase in UNCERTAINTY_PHRASES
    )

REFUSAL_PHRASES = (
    "i cannot answer",
    "i can't answer",
    "i cannot help",
    "i can't help",
    "i don't know",
    "i do not know",

    "i don't have enough information",
    "i do not have enough information",

    "not enough information",
    "insufficient information",

    "i'm unable to answer",
    "i am unable to answer",
    "unable to answer",

    "cannot determine",
    "can't determine",

    "cannot confirm",
    "can't confirm",

    "not available in the provided context",
    "not available in the context",
    "not available in the available knowledge",

    "not provided in the context",
    "not mentioned in the context",
    "not specified in the context",

    "not provided in the available knowledge",
    "not mentioned in the available knowledge",
    "not specified in the available knowledge",

    "the context does not provide",
    "the context doesn't provide",

    "the available knowledge does not provide",
    "the available knowledge doesn't provide",
)


def contains_refusal(answer: str) -> bool:
    """
    Detect explicit refusal or inability to answer
    from the available knowledge.
    """

    normalized = normalize_text(answer)

    if not normalized:
        return False

    return any(
        phrase in normalized
        for phrase in REFUSAL_PHRASES
    )

def answer_mentions_unknown_information(
    answer: str,
) -> bool:
    """
    Detect whether an answer acknowledges that
    information is unavailable or uncertain.
    """

    normalized = normalize_text(answer)

    return any(
        phrase in normalized
        for phrase in UNCERTAINTY_PHRASES
    )


def contains_uncertainty(
    answer: str,
) -> bool:
    """
    Alias for uncertainty detection used by the
    hallucination report.
    """

    return answer_mentions_unknown_information(
        answer
    )


def contains_refusal(
    answer: str,
) -> bool:
    """
    Detect explicit refusal or uncertainty.
    """

    normalized = normalize_text(answer)

    return any(
        phrase in normalized
        for phrase in REFUSAL_PHRASES
    )


# ============================================================
# Retrieved-context grounding
# ============================================================


def contains_chunk_content(
    answer: str,
    documents: list[dict[str, Any]],
) -> bool:
    """
    Determine whether the generated answer contains
    meaningful information from retrieved documents.

    The check is intentionally conservative.

    It does not require the entire document to appear
    verbatim in the answer.

    Instead it checks:

        1. Exact short-document matches.
        2. Meaningful word overlap for larger documents.
    """

    if not answer.strip():
        return False

    normalized_answer = normalize_text(answer)

    for document in documents:
        text = document.get(
            "text",
            "",
        )

        if not isinstance(text, str):
            continue

        normalized_text = normalize_text(text)

        if not normalized_text:
            continue

        # ----------------------------------------------------
        # Exact match for short documents.
        # ----------------------------------------------------

        if len(normalized_text) <= 120:
            if normalized_text in normalized_answer:
                return True

        # ----------------------------------------------------
        # Meaningful word overlap.
        # ----------------------------------------------------

        words = [
            word
            for word in normalized_text.split()
            if len(word) >= 5
        ]

        if not words:
            continue

        unique_words = set(words)

        matching_words = sum(
            1
            for word in unique_words
            if word in normalized_answer
        )

        overlap_ratio = (
            matching_words / len(unique_words)
        )

        if overlap_ratio >= 0.20:
            return True

    return False


# ============================================================
# Pipeline helper
# ============================================================


async def run_pipeline(
    query: str,
) -> str:
    """
    Run the real production RAG pipeline.

    RAGPipeline.run() requires:

        conversation_id
        message

    A fresh conversation ID is used for each evaluation
    query so previous evaluation cases cannot influence
    the current answer.
    """

    conversation_id = str(uuid4())

    result = await rag_pipeline.run(
        conversation_id=conversation_id,
        message=query,
    )

    if not isinstance(result, str):
        raise TypeError(
            "RAGPipeline.run() must return a string."
        )

    return result.strip()


# ============================================================
# 1. Unsupported questions
# ============================================================


@pytest.mark.asyncio
async def test_hallucination_on_unsupported_questions(
    rag_services,
):
    """
    Verify that unsupported questions do not produce
    confident hallucinated answers.

    Expected behavior:

        - No supporting context should be retrieved.
        - The answer should acknowledge uncertainty/refuse.

    Potential hallucination:

        no context
        AND
        no uncertainty/refusal
    """

    dataset = load_dataset()

    evaluated = 0
    hallucinations = 0

    print()
    print("=" * 70)
    print("RAG HALLUCINATION EVALUATION")
    print("=" * 70)

    for item in dataset:
        case_type = get_case_type(item)

        if case_type != "unsupported":
            continue

        query = get_query(item)

        documents = await rag_retriever.retrieve(
            query
        )

        answer = await run_pipeline(query)

        evaluated += 1

        has_context = bool(documents)

        refused = (
            answer_mentions_unknown_information(
                answer
            )
        )

        hallucinated = (
            not has_context
            and not refused
        )

        if hallucinated:
            hallucinations += 1

        retrieved_ids = [
            str(document.get("chunk_id"))
            for document in documents
        ]

        print()
        print(f"Query: {query}")
        print(
            f"Retrieved chunks: "
            f"{len(documents)}"
        )
        print(
            f"Retrieved IDs: "
            f"{retrieved_ids}"
        )
        print(
            f"Refusal/uncertainty: "
            f"{refused}"
        )
        print(
            f"Potential hallucination: "
            f"{hallucinated}"
        )
        print(
            f"Answer: {answer}"
        )

    if evaluated == 0:
        pytest.skip(
            "No unsupported hallucination cases "
            "found in dataset."
        )

    hallucination_rate = (
        hallucinations / evaluated
    )

    print()
    print("-" * 70)
    print(
        f"Unsupported cases: "
        f"{evaluated}"
    )
    print(
        f"Potential hallucinations: "
        f"{hallucinations}"
    )
    print(
        f"Hallucination rate: "
        f"{hallucination_rate:.4f}"
    )
    print("=" * 70)

    assert hallucination_rate <= 0.20, (
        "Hallucination rate is too high: "
        f"{hallucination_rate:.4f}"
    )


# ============================================================
# 2. Supported questions
# ============================================================


@pytest.mark.asyncio
async def test_supported_questions_use_context(
    rag_services,
):
    """
    Verify that supported questions retrieve context
    and generate answers grounded in that context.
    """

    dataset = load_dataset()

    evaluated = 0
    grounded = 0

    print()
    print("=" * 70)
    print("SUPPORTED QUESTION GROUNDING EVALUATION")
    print("=" * 70)

    for item in dataset:
        case_type = get_case_type(item)

        if case_type != "supported":
            continue

        query = get_query(item)

        documents = await rag_retriever.retrieve(
            query
        )

        if not documents:
            print()
            print(f"Query: {query}")
            print("Retrieved chunks: 0")
            print(
                "Skipping: no context retrieved."
            )
            continue

        answer = await run_pipeline(query)

        evaluated += 1

        uses_context = contains_chunk_content(
            answer,
            documents,
        )

        if uses_context:
            grounded += 1

        retrieved_ids = [
            str(document.get("chunk_id"))
            for document in documents
        ]

        print()
        print(f"Query: {query}")
        print(
            f"Retrieved chunks: "
            f"{len(documents)}"
        )
        print(
            f"Retrieved IDs: "
            f"{retrieved_ids}"
        )
        print(
            f"Grounded in context: "
            f"{uses_context}"
        )
        print(
            f"Answer: {answer}"
        )

    if evaluated == 0:
        pytest.skip(
            "No supported hallucination cases "
            "with retrieved context found in dataset."
        )

    grounding_rate = (
        grounded / evaluated
    )

    print()
    print("-" * 70)
    print(
        f"Supported cases: "
        f"{evaluated}"
    )
    print(
        f"Grounded answers: "
        f"{grounded}"
    )
    print(
        f"Grounding rate: "
        f"{grounding_rate:.4f}"
    )
    print("=" * 70)

    assert grounding_rate >= 0.50, (
        "Too many supported questions "
        "produced answers without clear "
        "evidence from retrieved context: "
        f"{grounding_rate:.4f}"
    )


# ============================================================
# 3. Partially supported questions
# ============================================================


@pytest.mark.asyncio
async def test_partially_supported_questions(
    rag_services,
):
    """
    Verify that partially supported questions do not
    cause the model to confidently invent unsupported
    information.

    Safe behavior:

        - The answer may contain supported information.
        - The answer should acknowledge information that
          cannot be established from the retrieved context.

    Therefore a safe partial answer requires:

        grounded
        AND
        uncertainty

    If retrieval returns no context, the answer is also
    considered safe because the model cannot legitimately
    provide a factual answer from the knowledge base.
    """

    dataset = load_dataset()

    evaluated = 0
    safe_answers = 0

    print()
    print("=" * 70)
    print("PARTIALLY SUPPORTED QUESTION EVALUATION")
    print("=" * 70)

    for item in dataset:
        case_type = get_case_type(item)

        if case_type != "partial":
            continue

        query = get_query(item)

        documents = await rag_retriever.retrieve(
            query
        )

        answer = await run_pipeline(query)

        evaluated += 1

        has_context = bool(documents)

        grounded = contains_chunk_content(
            answer,
            documents,
        )

        uncertainty = contains_uncertainty(
            answer
        )

        # ----------------------------------------------------
        # Safe partial answer.
        #
        # If context exists:
        #
        #     grounded + uncertainty
        #
        # If context does not exist:
        #
        #     uncertainty/refusal
        # ----------------------------------------------------

        if has_context:
            safe = (
                grounded
                and uncertainty
            )
        else:
            safe = uncertainty

        if safe:
            safe_answers += 1

        retrieved_ids = [
            str(document.get("chunk_id"))
            for document in documents
        ]

        print()
        print(f"Query: {query}")
        print(
            f"Retrieved chunks: "
            f"{len(documents)}"
        )
        print(
            f"Retrieved IDs: "
            f"{retrieved_ids}"
        )
        print(
            f"Context available: "
            f"{has_context}"
        )
        print(
            f"Grounded: "
            f"{grounded}"
        )
        print(
            f"Uncertainty detected: "
            f"{uncertainty}"
        )
        print(
            f"Safe answer: "
            f"{safe}"
        )
        print(
            f"Answer: {answer}"
        )

    if evaluated == 0:
        pytest.skip(
            "No partially supported hallucination "
            "cases found in dataset."
        )

    safety_rate = (
        safe_answers / evaluated
    )

    print()
    print("-" * 70)
    print(
        f"Partially supported cases: "
        f"{evaluated}"
    )
    print(
        f"Safe answers: "
        f"{safe_answers}"
    )
    print(
        f"Safety rate: "
        f"{safety_rate:.4f}"
    )
    print("=" * 70)

    assert safety_rate >= 0.50, (
        "Too many partially supported questions "
        "produced potentially unsafe answers: "
        f"{safety_rate:.4f}"
    )


# ============================================================
# 4. Complete hallucination evaluation report
# ============================================================


@pytest.mark.asyncio
async def test_hallucination_evaluation_report(
    rag_services,
):
    """
    Run the complete hallucination evaluation and
    write a machine-readable JSON report.

    The report can be used for regression testing.
    """

    dataset = load_dataset()

    results: list[dict[str, Any]] = []

    print()
    print("=" * 70)
    print("GENERATING HALLUCINATION EVALUATION REPORT")
    print("=" * 70)

    for item in dataset:
        query = get_query(item)

        case_type = get_case_type(item)

        relevant_ids = get_relevant_chunk_ids(
            item
        )

        # ----------------------------------------------------
        # Retrieve once for evaluation.
        # ----------------------------------------------------

        documents = await rag_retriever.retrieve(
            query
        )

        # ----------------------------------------------------
        # Run production RAG pipeline.
        # ----------------------------------------------------

        answer = await run_pipeline(query)

        retrieved_ids = [
            str(document.get("chunk_id"))
            for document in documents
        ]

        has_context = bool(documents)

        refusal = contains_refusal(
            answer
        )

        grounded = contains_chunk_content(
            answer,
            documents,
        )

        uncertainty = contains_uncertainty(
            answer
        )

        # ----------------------------------------------------
        # Evaluate case.
        # ----------------------------------------------------

        if case_type == "unsupported":
            passed = (
                not has_context
                and refusal
            )

        elif case_type == "supported":
            passed = (
                has_context
                and grounded
            )

        elif case_type == "partial":
            if has_context:
                passed = (
                    grounded
                    and uncertainty
                )
            else:
                passed = uncertainty

        else:
            passed = False

        result = {
            "query": query,
            "type": case_type,
            "expected_chunk_ids": sorted(
                relevant_ids
            ),
            "retrieved_chunk_ids": retrieved_ids,
            "has_context": has_context,
            "refusal_detected": refusal,
            "uncertainty_detected": uncertainty,
            "grounded": grounded,
            "passed": passed,
            "answer": answer,
        }

        results.append(result)

        print()
        print(f"Query: {query}")
        print(
            f"Type: {case_type}"
        )
        print(
            f"Expected chunks: "
            f"{relevant_ids}"
        )
        print(
            f"Retrieved chunks: "
            f"{retrieved_ids}"
        )
        print(
            f"Context available: "
            f"{has_context}"
        )
        print(
            f"Refusal detected: "
            f"{refusal}"
        )
        print(
            f"Uncertainty detected: "
            f"{uncertainty}"
        )
        print(
            f"Grounded: "
            f"{grounded}"
        )
        print(
            f"Passed: "
            f"{passed}"
        )
        print(
            f"Answer: {answer}"
        )

    # --------------------------------------------------------
    # Ensure report directory exists.
    # --------------------------------------------------------

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    passed_cases = sum(
        1
        for result in results
        if result["passed"]
    )

    failed_cases = sum(
        1
        for result in results
        if not result["passed"]
    )

    # --------------------------------------------------------
    # Build report.
    # --------------------------------------------------------

    report = {
        "evaluation": "hallucination",
        "dataset": str(DATASET_PATH),
        "total_cases": len(results),
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "pass_rate": (
            passed_cases / len(results)
            if results
            else 0.0
        ),
        "results": results,
    }

    # --------------------------------------------------------
    # Write JSON report.
    # --------------------------------------------------------

    with REPORT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print()
    print("=" * 70)
    print(
        "Hallucination report written to:"
    )
    print(
        REPORT_PATH
    )
    print(
        f"Total cases: {len(results)}"
    )
    print(
        f"Passed cases: {passed_cases}"
    )
    print(
        f"Failed cases: {failed_cases}"
    )

    if results:
        print(
            f"Pass rate: "
            f"{report['pass_rate']:.4f}"
        )

    print("=" * 70)

    # --------------------------------------------------------
    # Dataset must contain cases.
    # --------------------------------------------------------

    assert results, (
        "No hallucination evaluation cases found."
    )