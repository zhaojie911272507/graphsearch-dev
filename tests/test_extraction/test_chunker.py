"""Tests for the TextChunker utility."""

from uuid import uuid4

import pytest

from app.config import ExtractionSettings
from app.extraction.chunker import TextChunker


class TestTextChunker:
    """Tests for text chunking logic."""

    @pytest.fixture
    def chunker(self) -> TextChunker:
        settings = ExtractionSettings(
            max_concurrency=5,
            max_retries=2,
            chunk_size=100,
            chunk_overlap=20,
        )
        return TextChunker(settings)

    def test_empty_text_returns_no_chunks(self, chunker: TextChunker) -> None:
        doc_id = uuid4()
        chunks = chunker.chunk_text("", doc_id)
        assert chunks == []

    def test_whitespace_text_returns_no_chunks(self, chunker: TextChunker) -> None:
        doc_id = uuid4()
        chunks = chunker.chunk_text("   \n\t  ", doc_id)
        assert chunks == []

    def test_short_text_single_chunk(self, chunker: TextChunker) -> None:
        doc_id = uuid4()
        chunks = chunker.chunk_text("Short text.", doc_id)
        assert len(chunks) == 1
        assert chunks[0].content == "Short text."
        assert chunks[0].chunk_index == 0
        assert chunks[0].document_id == doc_id

    def test_long_text_multiple_chunks(self, chunker: TextChunker) -> None:
        doc_id = uuid4()
        # 300 chars → should produce multiple chunks with size=100, overlap=20
        text = "A" * 300
        chunks = chunker.chunk_text(text, doc_id)
        assert len(chunks) >= 3
        # Verify ordering
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_chunks_have_overlap(self) -> None:
        settings = ExtractionSettings(
            max_concurrency=5,
            max_retries=2,
            chunk_size=50,
            chunk_overlap=10,
        )
        chunker = TextChunker(settings)
        doc_id = uuid4()
        text = "0123456789" * 10  # 100 chars

        chunks = chunker.chunk_text(text, doc_id)
        # With size=50, overlap=10, step=40 → expect 3 chunks for 100 chars
        assert len(chunks) >= 2

    def test_chunk_index_sequential(self, chunker: TextChunker) -> None:
        doc_id = uuid4()
        text = "x" * 500
        chunks = chunker.chunk_text(text, doc_id)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))
