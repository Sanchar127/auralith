from __future__ import annotations

import re

from pydantic import ValidationError

from app.core.logger import logger
from app.services.rag.output_schema import RAGResponse


SOURCE_PATTERN = re.compile(r"^SOURCE:\d+$")


def validate_rag_response(
    data: dict,
) -> RAGResponse:
    """
    Validate and normalize a structured RAG response.

    Expected structure:

        {
            "answer": "...",
            "sources": ["SOURCE:1", "SOURCE:2"]
        }

    Validation performed:

    1. Validate the response against the Pydantic schema.
    2. Ensure the answer is not empty.
    3. Ensure every source follows the SOURCE:N format.
    4. Return a validated RAGResponse instance.

    Raises:
        ValidationError:
            If the response does not match the RAGResponse schema.

        ValueError:
            If the response contains invalid source labels.
    """

    try:
        response = RAGResponse.model_validate(data)

    except ValidationError as exc:
        logger.warning(
            "Invalid RAG response structure: %s",
            exc,
        )

        # Preserve the original Pydantic ValidationError.
        raise

    invalid_sources = [
        source
        for source in response.sources
        if not SOURCE_PATTERN.fullmatch(source)
    ]

    if invalid_sources:
        logger.warning(
            "LLM returned invalid source labels: %s",
            invalid_sources,
        )

        raise ValueError(
            "LLM returned invalid source labels: "
            f"{invalid_sources}"
        )

    return response