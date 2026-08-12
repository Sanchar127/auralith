from __future__ import annotations

import re

import pytest

from app.services.rag.pipeline import rag_pipeline
from app.services.rag.retriever import rag_retriever


# ==========================================================
# Test configuration
# ==========================================================

SUPPORTED_QUERY = "What audio formats are supported?"

UNSUPPORTED_QUERY = "Who invented audio enhancement technology?"

PARTIAL_QUERY = (
    "What audio formats are supported and who invented "
    "audio enhancement technology?"
)


# ==========================================================
# Helpers
# ==========================================================


def normalize_text(text: str) -> str:
    """
    Normalize text for simple factual checks.
    """

    return re.sub(
        r"\s+",
        " ",
        text.lower().strip(),
    )


def extract_retrieved_text(
    documents: list[dict],
) -> str:
    """
    Combine retrieved document text into one normalized
    context string.
    """

    return normalize_text(
        " ".join(
            str(document.get("text", ""))
            for document in documents
        )
    )


def get_chunk_ids(
    documents: list[dict],
) -> list[str]:
    """
    Return retrieved chunk IDs for readable evaluation logs.
    """

    return [
        str(document.get("chunk_id"))
        for document in documents
    ]


def contains_supported_fact(
    answer: str,
    context: str,
) -> bool:
    """
    Check whether the answer contains at least one
    recognizable factual term that is also present
    in the retrieved context.

    This is intentionally lightweight.

    It does not attempt full semantic entailment.
    """

    answer_normalized = normalize_text(answer)
    context_normalized = normalize_text(context)

    factual_terms = [
        "wav",
        "mp3",
        "audio enhancement",
        "noise reduction",
        "filtering",
        "denoising",
        "audio quality",
    ]

    return any(
        term in answer_normalized
        and term in context_normalized
        for term in factual_terms
    )


def contains_uncertainty_statement(
    answer: str,
) -> bool:
    """
    Detect whether the model acknowledges that the
    available knowledge is insufficient.

    This intentionally checks behavior rather than
    requiring an exact sentence.
    """

    normalized = normalize_text(answer)

    uncertainty_patterns = [
        "not enough information",
        "does not contain enough information",
        "available knowledge does not",
        "available knowledge is insufficient",
        "i don't have enough information",
        "information is not available",
        "could not find",
        "cannot determine",
        "unable to determine",
        "not provided",
        "not specified",
        "does not provide",
        "not contain information",
        "no information",
        "information is unavailable",
        "not available in the retrieved",
        "not available in the knowledge",
    ]

    return any(
        pattern in normalized
        for pattern in uncertainty_patterns
    )


def contains_supported_format(
    answer: str,
    context: str,
) -> bool:
    """
    Check whether the answer mentions an audio format
    that is actually present in the retrieved context.

    This is important for partial-support testing:
    we should not require WAV/MP3 if those facts were
    not retrieved for the particular query.
    """

    answer_normalized = normalize_text(answer)
    context_normalized = normalize_text(context)

    supported_formats = [
        "wav",
        "mp3",
        "flac",
        "aac",
        "aiff",
        "ac-3",
        "opus",
        "alac",
    ]

    return any(
        audio_format in answer_normalized
        and audio_format in context_normalized
        for audio_format in supported_formats
    )


def contains_unsupported_inventor_claim(
    answer: str,
) -> bool:
    """
    Detect confident inventor claims.

    The knowledge base does not provide an inventor, so
    the model must not confidently claim that someone
    invented audio enhancement technology.
    """

    normalized = normalize_text(answer)

    fabricated_claim_patterns = [
        r"\binvented by\b",
        r"\binventor was\b",
        r"\bthe inventor is\b",
        r"\bthe inventor was\b",
        r"\bcreated by\b",
        r"\bdeveloped by\b",
        r"\bwas invented by\b",
    ]

    return any(
        re.search(
            pattern,
            normalized,
        )
        for pattern in fabricated_claim_patterns
    )


# ==========================================================
# Faithfulness
# ==========================================================


@pytest.mark.asyncio
async def test_answer_is_supported_by_retrieved_context():
    """
    Verify that an answer to a supported question contains
    information that exists in the retrieved knowledge.
    """

    documents = await rag_retriever.retrieve(
        SUPPORTED_QUERY
    )

    assert documents, (
        "Expected retrieved documents for the supported query."
    )

    context = extract_retrieved_text(
        documents
    )

    answer = await rag_pipeline.run(
        conversation_id="evaluation-faithfulness-supported",
        message=SUPPORTED_QUERY,
    )

    assert answer

    print(
        "\n"
        "============================================================\n"
        "FAITHFULNESS - SUPPORTED QUESTION\n"
        "============================================================\n"
        f"Retrieved chunks: {get_chunk_ids(documents)}\n\n"
        f"Context:\n{context}\n\n"
        f"Answer:\n{answer}\n"
        "============================================================"
    )

    assert contains_supported_fact(
        answer,
        context,
    ), (
        "Answer does not contain a recognizable fact "
        "supported by the retrieved context.\n\n"
        f"Answer:\n{answer}\n\n"
        f"Context:\n{context}"
    )


# ==========================================================
# Unsupported question
# ==========================================================


@pytest.mark.asyncio
async def test_unsupported_question_does_not_use_pretrained_knowledge():
    """
    Verify that the model does not answer an unsupported
    historical question using pretrained knowledge.

    The evaluation knowledge does not identify an inventor
    of audio enhancement technology.
    """

    documents = await rag_retriever.retrieve(
        UNSUPPORTED_QUERY
    )

    context = extract_retrieved_text(
        documents
    )

    answer = await rag_pipeline.run(
        conversation_id="evaluation-faithfulness-unsupported",
        message=UNSUPPORTED_QUERY,
    )

    assert answer

    print(
        "\n"
        "============================================================\n"
        "FAITHFULNESS - UNSUPPORTED QUESTION\n"
        "============================================================\n"
        f"Retrieved chunks: {get_chunk_ids(documents)}\n\n"
        f"Context:\n{context}\n\n"
        f"Answer:\n{answer}\n"
        "============================================================"
    )

    assert contains_uncertainty_statement(
        answer
    ), (
        "The model appears to answer an unsupported "
        "question without acknowledging missing information.\n\n"
        f"Answer:\n{answer}\n\n"
        f"Context:\n{context}"
    )

    assert not contains_unsupported_inventor_claim(
        answer
    ), (
        "The answer contains a potentially fabricated "
        "inventor claim.\n\n"
        f"Answer:\n{answer}\n\n"
        f"Context:\n{context}"
    )


# ==========================================================
# No fabricated person
# ==========================================================


@pytest.mark.asyncio
async def test_answer_does_not_invent_unknown_person():
    """
    Verify that the model does not invent a person when
    the retrieved knowledge contains no inventor information.
    """

    documents = await rag_retriever.retrieve(
        UNSUPPORTED_QUERY
    )

    context = extract_retrieved_text(
        documents
    )

    answer = await rag_pipeline.run(
        conversation_id="evaluation-faithfulness-no-invented-person",
        message=UNSUPPORTED_QUERY,
    )

    assert answer

    normalized_answer = normalize_text(
        answer
    )

    print(
        "\n"
        "============================================================\n"
        "FAITHFULNESS - NO INVENTED PERSON\n"
        "============================================================\n"
        f"Retrieved chunks: {get_chunk_ids(documents)}\n\n"
        f"Context:\n{context}\n\n"
        f"Answer:\n{answer}\n"
        "============================================================"
    )

    assert contains_uncertainty_statement(
        answer
    ), (
        "Answer did not acknowledge that the inventor "
        "information is unavailable.\n\n"
        f"Answer:\n{answer}"
    )

    assert not contains_unsupported_inventor_claim(
        normalized_answer
    ), (
        "Potential unsupported inventor claim detected.\n\n"
        f"Answer:\n{answer}"
    )


# ==========================================================
# Partial support
# ==========================================================


@pytest.mark.asyncio
async def test_partially_supported_question_does_not_complete_missing_information():
    """
    Verify behavior when a question contains both:

        1. A potentially supported part.
        2. An unsupported part.

    The important rule here is:

        The answer must only use information that was
        actually retrieved.

    We intentionally do NOT require WAV or MP3 to be
    retrieved. Retrieval quality is evaluated separately.

    If an audio format exists in the retrieved context,
    the answer should be allowed to address that portion.

    The inventor portion must remain unsupported.
    """

    documents = await rag_retriever.retrieve(
        PARTIAL_QUERY
    )

    assert documents, (
        "Expected at least one retrieved document for "
        "the partially supported query."
    )

    context = extract_retrieved_text(
        documents
    )

    answer = await rag_pipeline.run(
        conversation_id="evaluation-faithfulness-partial",
        message=PARTIAL_QUERY,
    )

    assert answer

    normalized_answer = normalize_text(
        answer
    )

    supported_format_was_retrieved = any(
        audio_format in context
        for audio_format in [
            "wav",
            "mp3",
            "flac",
            "aac",
            "aiff",
            "ac-3",
            "opus",
            "alac",
        ]
    )

    supported_format_present = contains_supported_format(
        answer,
        context,
    )

    print(
        "\n"
        "============================================================\n"
        "FAITHFULNESS - PARTIALLY SUPPORTED QUESTION\n"
        "============================================================\n"
        f"Retrieved chunks: {get_chunk_ids(documents)}\n\n"
        f"Supported format retrieved: "
        f"{supported_format_was_retrieved}\n\n"
        f"Context:\n{context}\n\n"
        f"Answer:\n{answer}\n"
        "============================================================"
    )

    # ------------------------------------------------------
    # If a supported format was actually retrieved, the
    # answer should be able to address that supported part.
    #
    # If retrieval did not return any format information,
    # we do NOT fail the faithfulness test. That is a
    # retrieval-quality problem, not a faithfulness problem.
    # ------------------------------------------------------

    if supported_format_was_retrieved:
        assert supported_format_present, (
            "The answer failed to address a supported fact "
            "that was actually present in the retrieved context.\n\n"
            f"Answer:\n{answer}\n\n"
            f"Context:\n{context}"
        )

    # ------------------------------------------------------
    # The unsupported inventor portion must not be invented.
    # ------------------------------------------------------

    assert contains_uncertainty_statement(
        answer
    ), (
        "The answer did not acknowledge that the unsupported "
        "inventor information is unavailable.\n\n"
        f"Answer:\n{answer}\n\n"
        f"Context:\n{context}"
    )

    assert not contains_unsupported_inventor_claim(
        normalized_answer
    ), (
        "The answer contains an unsupported inventor claim.\n\n"
        f"Answer:\n{answer}\n\n"
        f"Context:\n{context}"
    )


# ==========================================================
# No unsupported technical claims
# ==========================================================


@pytest.mark.asyncio
async def test_supported_answer_does_not_add_obviously_unsupported_details():
    """
    Verify that a supported answer does not introduce
    unrelated technical details that are absent from the
    retrieved knowledge.
    """

    documents = await rag_retriever.retrieve(
        SUPPORTED_QUERY
    )

    assert documents

    context = extract_retrieved_text(
        documents
    )

    answer = await rag_pipeline.run(
        conversation_id="evaluation-faithfulness-no-extra-details",
        message=SUPPORTED_QUERY,
    )

    assert answer

    normalized_answer = normalize_text(
        answer
    )

    print(
        "\n"
        "============================================================\n"
        "FAITHFULNESS - NO UNSUPPORTED TECHNICAL DETAILS\n"
        "============================================================\n"
        f"Retrieved chunks: {get_chunk_ids(documents)}\n\n"
        f"Context:\n{context}\n\n"
        f"Answer:\n{answer}\n"
        "============================================================"
    )

    # ------------------------------------------------------
    # These are examples of technical details that should
    # not appear unless they are actually present in the
    # retrieved context.
    # ------------------------------------------------------

    unsupported_terms = [
        "24-bit",
        "16-bit",
        "44.1 khz",
        "48 khz",
        "96 khz",
        "stereo",
        "lossless",
        "flac",
        "aac",
        "alac",
        "opus",
    ]

    for term in unsupported_terms:
        if term in normalized_answer:
            assert term in context, (
                f"Unsupported technical detail '{term}' "
                "appeared in the answer but was not found "
                "in the retrieved context.\n\n"
                f"Answer:\n{answer}\n\n"
                f"Context:\n{context}"
            )