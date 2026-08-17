from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.services.rag.output_schema import RAGResponse
from app.services.rag.output_validator import (
    validate_rag_response,
)


def test_valid_structured_response():
    response = validate_rag_response(
        {
            "answer": "WAV and MP3 are supported.",
            "sources": [
                "SOURCE:1",
            ],
        }
    )

    assert response.answer == (
        "WAV and MP3 are supported."
    )

    assert response.sources == [
        "SOURCE:1",
    ]


def test_sources_default_to_empty_list():
    response = validate_rag_response(
        {
            "answer": "The information is unavailable.",
        }
    )

    assert response.answer
    assert response.sources == []


def test_empty_answer_is_rejected():
    with pytest.raises(ValidationError):
        validate_rag_response(
            {
                "answer": "",
                "sources": [],
            }
        )


def test_invalid_source_label_is_rejected():
    with pytest.raises(ValueError):
        validate_rag_response(
            {
                "answer": "WAV and MP3 are supported.",
                "sources": [
                    "SOURCE:999",
                    "invalid-source",
                ],
            }
        )


def test_missing_answer_is_rejected():
    with pytest.raises(ValidationError):
        validate_rag_response(
            {
                "sources": [
                    "SOURCE:1",
                ],
            }
        )


def test_wrong_answer_type_is_rejected():
    with pytest.raises(ValidationError):
        validate_rag_response(
            {
                "answer": 123,
                "sources": [],
            }
        )