"""Tests for API request/response schemas."""

import pytest
from pydantic import ValidationError

from app.domain.schemas import (
    IngestRequest,
    IngestResponse,
    QueryRequest,
    RetrievalContext,
    RetrievedChunk,
)
from uuid import uuid4


class TestIngestRequest:
    """Tests for IngestRequest validation."""

    def test_valid_request(self) -> None:
        req = IngestRequest(
            title="Test Doc",
            content="Some content here",
            source_url="https://example.com",
        )
        assert req.title == "Test Doc"

    def test_empty_title_rejected(self) -> None:
        with pytest.raises(ValidationError):
            IngestRequest(title="", content="Some content")

    def test_empty_content_rejected(self) -> None:
        with pytest.raises(ValidationError):
            IngestRequest(title="Test", content="")


class TestQueryRequest:
    """Tests for QueryRequest validation."""

    def test_valid_query(self) -> None:
        req = QueryRequest(question="What is Graph RAG?")
        assert req.top_k == 10  # default
        assert req.traversal_depth == 2  # default

    def test_top_k_bounds(self) -> None:
        with pytest.raises(ValidationError):
            QueryRequest(question="Test", top_k=0)
        with pytest.raises(ValidationError):
            QueryRequest(question="Test", top_k=101)


class TestRetrievalContext:
    """Tests for RetrievalContext formatting."""

    def test_empty_context(self) -> None:
        ctx = RetrievalContext()
        assert ctx.formatted_context == ""

    def test_formatted_context_with_chunks(self) -> None:
        ctx = RetrievalContext(
            chunks=[
                RetrievedChunk(
                    chunk_id=uuid4(),
                    content="Graph databases store relationships natively.",
                    score=0.95,
                    chunk_index=0,
                ),
            ]
        )
        formatted = ctx.formatted_context
        assert "Relevant Text Chunks" in formatted
        assert "Graph databases" in formatted
        assert "0.950" in formatted
