from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.logger import logger


@dataclass
class DocumentChunk:
    """
    Represents a single RAG chunk.
    """

    text: str
    metadata: dict[str, Any]


class TextChunker:
    """
    Splits documents into smaller chunks
    for embedding and retrieval.
    """

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        """
        Split text into chunks.

        Args:
            text:
                Raw document content.

            metadata:
                Extra information stored with
                the vector.

        Returns:
            List of DocumentChunk objects.
        """

        if not text.strip():
            return []

        metadata = metadata or {}

        logger.info(
            "Chunking document. characters=%s",
            len(text),
        )

        chunks = []

        start = 0
        text_length = len(text)

        chunk_number = 0

        while start < text_length:

            end = start + self.chunk_size

            chunk = text[start:end]

            # Try to end at a sentence boundary
            if end < text_length:

                last_period = chunk.rfind(".")

                last_newline = chunk.rfind("\n")

                boundary = max(
                    last_period,
                    last_newline,
                )

                if boundary > 200:
                    end = start + boundary + 1
                    chunk = text[start:end]

            chunk = chunk.strip()

            if chunk:

                chunks.append(
                    DocumentChunk(
                        text=chunk,
                        metadata={
                            **metadata,
                            "chunk_id": chunk_number,
                        },
                    )
                )

                chunk_number += 1

            start = (
                end - self.chunk_overlap
            )

            if start < 0:
                start = 0

        logger.info(
            "Created %s chunks.",
            len(chunks),
        )

        return chunks


chunker = TextChunker()