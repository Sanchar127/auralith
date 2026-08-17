from __future__ import annotations

from pydantic import BaseModel, Field


class RAGResponse(BaseModel):
    """
    Structured response returned by the RAG LLM.

    The model must provide an answer and may provide
    source labels corresponding to retrieved context.
    """

    answer: str = Field(
        min_length=1,
        description="The final answer to the user's question.",
    )

    sources: list[str] = Field(
        default_factory=list,
        description=(
            "Retrieved source labels used to support "
            "the answer, such as SOURCE:1."
        ),
    )