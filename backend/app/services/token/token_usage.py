from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """
    Token usage produced by an LLM request.
    """

    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
        )

    def __post_init__(self) -> None:

        if self.input_tokens < 0:
            raise ValueError(
                "input_tokens cannot be negative"
            )

        if self.output_tokens < 0:
            raise ValueError(
                "output_tokens cannot be negative"
            )