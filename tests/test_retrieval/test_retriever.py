"""Unit tests for the retrieval module."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.enums import EntityType, RelationType
from app.domain.schemas import RetrievedChunk, RetrievedEntity, RetrievedRelation
from app.retrieval.retriever import GraphRetriever


class TestGraphRetriever:
    """Tests for GraphRetriever class."""

    @pytest.fixture
    def mock_graph_store(self):
        """Create a mock GraphStore."""
        store = MagicMock()
        store.vector_search = AsyncMock(return_value=[])
        store.traverse_from_chunks = AsyncMock(return_value=[])
        return store

    @pytest.fixture
    def mock_embedding_service(self):
        """Create a mock EmbeddingService."""
        service = MagicMock()
        service.embed_query = AsyncMock(return_value=[0.1] * 1024)
        return service

    @pytest.fixture
    def retriever(self, mock_graph_store, mock_embedding_service):
        """Create a GraphRetriever with mocked dependencies."""
        return GraphRetriever(mock_graph_store, mock_embedding_service)

    @pytest.mark.asyncio
    async def test_retrieve_empty_query_returns_empty_context(self, retriever, mock_graph_store):
        """Test that empty vector search returns empty context."""
        mock_graph_store.vector_search = AsyncMock(return_value=[])

        result = await retriever.retrieve(
            query="test query",
            top_k=10,
        )

        assert result.chunks == []
        assert result.entities == []
        assert result.relations == []

    @pytest.mark.asyncio
    async def test_retrieve_with_vector_results(self, retriever, mock_graph_store):
        """Test retrieval with vector search results."""
        mock_graph_store.vector_search = AsyncMock(return_value=[
            {
                "node": {
                    "id": str(uuid4()),
                    "content": "Test chunk content",
                    "score": 0.95,
                    "document_title": "Test Doc",
                    "chunk_index": 0,
                },
                "score": 0.95,
            }
        ])

        result = await retriever.retrieve(
            query="test query",
            top_k=10,
        )

        assert len(result.chunks) == 1
        assert result.chunks[0].content == "Test chunk content"
        assert result.chunks[0].score == 0.95

    @pytest.mark.asyncio
    async def test_retrieve_vector_only_mode(self, retriever, mock_graph_store):
        """Test vector-only retrieval skips graph traversal."""
        mock_graph_store.vector_search = AsyncMock(return_value=[
            {
                "node": {
                    "id": str(uuid4()),
                    "content": "Test chunk",
                    "score": 0.9,
                    "document_title": "Test",
                    "chunk_index": 0,
                },
                "score": 0.9,
            }
        ])

        result = await retriever.retrieve(
            query="test",
            top_k=10,
            vector_only=True,
        )

        assert len(result.chunks) == 1
        mock_graph_store.traverse_from_chunks.assert_not_called()

    @pytest.mark.asyncio
    async def test_retrieve_with_entity_filter(self, retriever, mock_graph_store):
        """Test retrieval with entity type filter."""
        mock_graph_store.vector_search = AsyncMock(return_value=[
            {
                "node": {
                    "id": str(uuid4()),
                    "content": "Test chunk",
                    "score": 0.9,
                    "document_title": "Test",
                    "chunk_index": 0,
                },
                "score": 0.9,
            }
        ])

        # Should pass entity_types to traverse_from_chunks
        await retriever.retrieve(
            query="test",
            top_k=10,
            entity_types=["Person", "Organization"],
        )

        mock_graph_store.traverse_from_chunks.assert_called_once()
        call_kwargs = mock_graph_store.traverse_from_chunks.call_args.kwargs
        assert call_kwargs.get("entity_types") == ["Person", "Organization"]

    @pytest.mark.asyncio
    async def test_retrieve_with_relation_filter(self, retriever, mock_graph_store):
        """Test retrieval with relation type filter."""
        mock_graph_store.vector_search = AsyncMock(return_value=[
            {
                "node": {
                    "id": str(uuid4()),
                    "content": "Test chunk",
                    "score": 0.9,
                    "document_title": "Test",
                    "chunk_index": 0,
                },
                "score": 0.9,
            }
        ])

        await retriever.retrieve(
            query="test",
            top_k=10,
            relation_types=["WORKS_AT", "KNOWS"],
        )

        call_kwargs = mock_graph_store.traverse_from_chunks.call_args.kwargs
        assert call_kwargs.get("relation_types") == ["WORKS_AT", "KNOWS"]

    def test_parse_vector_results_with_dict_node(self, retriever):
        """Test parsing vector results with dict-style node."""
        records = [
            {
                "node": {
                    "id": str(uuid4()),
                    "content": "Test content",
                    "score": 0.8,
                    "document_title": "Doc",
                    "chunk_index": 1,
                },
                "score": 0.8,
            }
        ]

        result = retriever._parse_vector_results(records)

        assert len(result) == 1
        assert result[0].content == "Test content"
        assert result[0].score == 0.8

    def test_parse_traversal_results_entity_deduplication(self, retriever):
        """Test that entities are deduplicated during parsing."""
        entity_id = str(uuid4())
        records = [
            {"neighbor": {"id": entity_id, "name": "Test Entity", "entity_type": "PERSON"}, "rels": []},
            {"neighbor": {"id": entity_id, "name": "Test Entity", "entity_type": "PERSON"}, "rels": []},
        ]

        entities, _ = retriever._parse_traversal_results(records)

        # Should only have one entity (deduplicated)
        assert len(entities) == 1


class TestRetrievalContext:
    """Tests for RetrievalContext."""

    def test_formatted_context_with_chunks(self):
        """Test formatted_context includes chunks."""
        from app.domain.schemas import RetrievalContext

        context = RetrievalContext(
            chunks=[
                RetrievedChunk(
                    chunk_id=uuid4(),
                    content="Test chunk",
                    score=0.9,
                    document_title="Doc",
                    chunk_index=0,
                )
            ]
        )

        formatted = context.formatted_context
        assert "Test chunk" in formatted
        assert "Relevant Text Chunks" in formatted

    def test_formatted_context_with_entities(self):
        """Test formatted_context includes entities."""
        from app.domain.schemas import RetrievalContext

        context = RetrievalContext(
            entities=[
                RetrievedEntity(
                    entity_id=uuid4(),
                    name="Test Entity",
                    entity_type=EntityType.PERSON,
                )
            ]
        )

        formatted = context.formatted_context
        assert "Test Entity" in formatted
        assert "Discovered Entities" in formatted

    def test_formatted_context_with_relations(self):
        """Test formatted_context includes relations."""
        from app.domain.schemas import RetrievalContext

        context = RetrievalContext(
            relations=[
                RetrievedRelation(
                    source_name="Person A",
                    target_name="Person B",
                    relation_type=RelationType.RELATED_TO,
                    weight=0.8,
                )
            ]
        )

        formatted = context.formatted_context
        assert "Person A" in formatted
        assert "RELATED_TO" in formatted
        assert "Graph Relations" in formatted
