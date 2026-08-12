
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.logger import logger


@dataclass
class DocumentChunk:
    """
    Represents a single RAG document chunk.
    """

    text: str
    metadata: dict[str, Any]


class TextChunker:
    """
    Splits documents into smaller chunks for embedding and retrieval.

    The chunker:
        - Splits text according to a maximum character size.
        - Maintains overlap between consecutive chunks.
        - Attempts to split at sentence or newline boundaries.
        - Preserves caller-provided metadata.
        - Generates a chunk ID when one is not provided.
    """

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 150,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError(
                "chunk_size must be greater than 0."
            )

        if chunk_overlap < 0:
            raise ValueError(
                "chunk_overlap cannot be negative."
            )

        if chunk_overlap >= chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than "
                "chunk_size."
            )

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        """
        Split a document into smaller chunks.

        Behavior:
            - Empty or whitespace-only input returns no chunks.
            - Existing metadata is preserved.
            - An explicitly supplied ``chunk_id`` is preserved.
            - If no ``chunk_id`` is supplied, a numeric chunk
              index is generated.
            - Chunks attempt to end at sentence/newline boundaries.
            - Chunk overlap is maintained between consecutive chunks.

        Args:
            text:
                The document text to split.

            metadata:
                Optional metadata to attach to every chunk.

        Returns:
            A list of ``DocumentChunk`` objects.
        """

        if not text.strip():
            return []

        base_metadata = dict(metadata or {})

        logger.info(
            "Chunking document. characters=%s",
            len(text),
        )

        chunks: list[DocumentChunk] = []

        text_length = len(text)
        start = 0
        chunk_number = 0

        while start < text_length:
            # --------------------------------------------------
            # Calculate the initial chunk boundary.
            # --------------------------------------------------

            end = min(
                start + self.chunk_size,
                text_length,
            )

            chunk_text = text[start:end]

            # --------------------------------------------------
            # Try to end the chunk at a natural boundary.
            #
            # Prefer:
            #   1. The last newline.
            #   2. The last period.
            #
            # Only use the boundary when enough text has
            # already been accumulated. This prevents creating
            # unnecessarily small chunks.
            # --------------------------------------------------

            if end < text_length:
                last_period = chunk_text.rfind(".")
                last_newline = chunk_text.rfind("\n")

                boundary = max(
                    last_period,
                    last_newline,
                )

                if boundary >= 200:
                    end = start + boundary + 1
                    chunk_text = text[start:end]

            # --------------------------------------------------
            # Remove leading/trailing whitespace from the chunk.
            # --------------------------------------------------

            chunk_text = chunk_text.strip()

            if chunk_text:
                # --------------------------------------------------
                # Copy metadata so each chunk gets its own dictionary.
                # --------------------------------------------------

                chunk_metadata = dict(base_metadata)

                # --------------------------------------------------
                # Preserve an explicitly provided chunk ID.
                #
                # If no chunk ID exists, generate one from the
                # chunk's sequential index.
                # --------------------------------------------------

                if "chunk_id" not in chunk_metadata:
                    chunk_metadata["chunk_id"] = chunk_number

                chunks.append(
                    DocumentChunk(
                        text=chunk_text,
                        metadata=chunk_metadata,
                    )
                )

                chunk_number += 1

            # --------------------------------------------------
            # Calculate the next chunk's starting position.
            #
            # Example:
            #
            # chunk_size    = 800
            # chunk_overlap = 150
            #
            # next_start = end - 150
            #
            # This means the next chunk shares 150 characters
            # with the previous chunk.
            # --------------------------------------------------

            next_start = end - self.chunk_overlap

            # --------------------------------------------------
            # Prevent an infinite loop.
            # --------------------------------------------------

            if next_start <= start:
                next_start = end

            start = next_start

        logger.info(
            "Created %s chunks.",
            len(chunks),
        )

        return chunks


chunker = TextChunker()
