"""Tests for the TextChunker utility.

Tests for semantic-aware chunking logic inspired by MiroFish.
"""

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
            chunk_strategy="fixed",
            chunk_token_size=64,  # Target token size
            chunk_overlap=16,
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
        # Text with paragraph breaks → should split by semantic boundaries
        text = "First paragraph. " * 20 + "\n\n" + "Second paragraph. " * 20
        chunks = chunker.chunk_text(text, doc_id)
        # Should produce multiple chunks based on semantic structure
        assert len(chunks) >= 2
        # Verify ordering
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_chunks_have_overlap(self) -> None:
        settings = ExtractionSettings(
            max_concurrency=5,
            max_retries=2,
            chunk_strategy="fixed",
            chunk_token_size=64,
            chunk_overlap=16,
        )
        chunker = TextChunker(settings)
        doc_id = uuid4()
        # Text with natural paragraph breaks
        text = "First part with sentences. " * 10 + "\n\n" + "Second part with more sentences. " * 10

        chunks = chunker.chunk_text(text, doc_id)
        assert len(chunks) >= 2

        # Verify overlap metadata is populated for chunks after the first
        chunks_with_overlap = [c for c in chunks if c.previous_chunk_overlap]
        assert len(chunks_with_overlap) >= 1

        # Verify that chunks have semantic boundaries marked
        for chunk in chunks:
            assert chunk.semantic_boundary_start is True
            assert chunk.semantic_boundary_end is True

    def test_chunk_index_sequential(self, chunker: TextChunker) -> None:
        doc_id = uuid4()
        text = "Sentence one. " * 50 + "\n\n" + "Sentence two. " * 50
        chunks = chunker.chunk_text(text, doc_id)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_semantic_metadata(self, chunker: TextChunker) -> None:
        """Test that chunks include semantic metadata."""
        doc_id = uuid4()
        text = """# Introduction

This is the introduction section with some content.

## Details

Here are the details with more information.

- List item 1
- List item 2
"""
        chunks = chunker.chunk_text(text, doc_id)

        assert len(chunks) >= 1

        # Verify metadata fields are populated
        for chunk in chunks:
            assert hasattr(chunk, 'section_title')
            assert hasattr(chunk, 'paragraph_type')
            assert hasattr(chunk, 'word_count')
            assert hasattr(chunk, 'sentence_count')
            assert chunk.semantic_boundary_start is True
            assert chunk.semantic_boundary_end is True

    def test_section_header_detection(self, chunker: TextChunker) -> None:
        """Test that section headers are detected and preserved."""
        doc_id = uuid4()
        text = """# Main Title

Content under main title.

## Sub Section

Content under subsection.
"""
        chunks = chunker.chunk_text(text, doc_id)

        # Should have section titles populated
        section_titles = [c.section_title for c in chunks]
        assert any('Main Title' in t or 'Sub Section' in t for t in section_titles)

    def test_paragraph_type_detection(self, chunker: TextChunker) -> None:
        """Test different paragraph types are detected."""
        doc_id = uuid4()

        # Test code block
        code_text = "```python\ncode here\n```"
        chunks = chunker.chunk_text(code_text, doc_id)
        assert any(c.paragraph_type == 'code' for c in chunks)

        # Test list
        list_text = "- Item 1\n- Item 2"
        chunks = chunker.chunk_text(list_text, doc_id)
        assert any(c.paragraph_type == 'list' for c in chunks)

        # Test header
        header_text = "# Header Title"
        chunks = chunker.chunk_text(header_text, doc_id)
        assert any(c.paragraph_type == 'header' for c in chunks)
