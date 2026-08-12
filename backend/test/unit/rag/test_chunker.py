from app.services.rag.chunker import (
    DocumentChunk,
    TextChunker,
)


def test_chunker_returns_chunks():
    chunker = TextChunker(
        chunk_size=500,
        chunk_overlap=50,
    )

    text = (
        "Auralith is an AI music platform. "
        * 100
    )

    chunks = chunker.split(text)

    assert chunks

    assert all(
        isinstance(chunk, DocumentChunk)
        for chunk in chunks
    )

    assert all(
        isinstance(chunk.text, str)
        for chunk in chunks
    )


def test_chunker_does_not_return_empty_chunks():
    chunker = TextChunker(
        chunk_size=500,
        chunk_overlap=50,
    )

    text = "Auralith generates music."

    chunks = chunker.split(text)

    assert chunks

    assert all(
        chunk.text.strip()
        for chunk in chunks
    )


def test_short_text_produces_chunk():
    chunker = TextChunker(
        chunk_size=500,
        chunk_overlap=50,
    )

    text = "Hello Auralith."

    chunks = chunker.split(text)

    assert len(chunks) == 1
    assert chunks[0].text == text


def test_chunk_metadata_contains_chunk_id():
    chunker = TextChunker(
        chunk_size=500,
        chunk_overlap=50,
    )

    text = "Auralith is an AI music platform."

    chunks = chunker.split(text)

    assert chunks

    for index, chunk in enumerate(chunks):
        assert chunk.metadata["chunk_id"] == index


def test_chunker_preserves_metadata():
    chunker = TextChunker(
        chunk_size=500,
        chunk_overlap=50,
    )

    text = "Auralith generates music."

    metadata = {
        "document_id": "doc-123",
        "source": "knowledge-base",
    }

    chunks = chunker.split(
        text,
        metadata=metadata,
    )

    assert len(chunks) == 1

    assert chunks[0].metadata["document_id"] == "doc-123"
    assert chunks[0].metadata["source"] == "knowledge-base"
    assert chunks[0].metadata["chunk_id"] == 0


def test_empty_text_returns_no_chunks():
    chunker = TextChunker(
        chunk_size=500,
        chunk_overlap=50,
    )

    chunks = chunker.split("")

    assert chunks == []


def test_whitespace_only_text_returns_no_chunks():
    chunker = TextChunker(
        chunk_size=500,
        chunk_overlap=50,
    )

    chunks = chunker.split("   \n\t  ")

    assert chunks == []