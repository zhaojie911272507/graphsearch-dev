"""Shared test fixtures.

Provides mock instances of all heavy services so unit tests
run without Neo4j, LLM APIs, or embedding models.
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import (
    EmbeddingSettings,
    ExtractionSettings,
    Neo4jSettings,
    OpenAISettings,
    RetrievalSettings,
    Settings,
)
from app.domain.enums import EntityType, NodeType, RelationType
from app.domain.nodes import ChunkNode, ConceptNode, DocumentNode, EntityNode
from app.domain.relationships import GraphRelationship


# ──────────────────────────────────────────
# Settings Fixtures
# ──────────────────────────────────────────


@pytest.fixture
def test_settings() -> Settings:
    """Provide test-safe settings that don't require real services."""
    with patch.object(EmbeddingSettings, "validate_model_path", return_value="./fake_model"):
        return Settings(
            neo4j=Neo4jSettings(uri="bolt://localhost:7687", password="test"),
            openai=OpenAISettings(api_key="sk-test-key"),
            embedding=EmbeddingSettings(model_path="./fake_model"),
            retrieval=RetrievalSettings(),
            extraction=ExtractionSettings(),
        )


# ──────────────────────────────────────────
# Domain Object Factories
# ──────────────────────────────────────────


@pytest.fixture
def sample_document() -> DocumentNode:
    """Create a sample DocumentNode for testing."""
    return DocumentNode(
        title="Test Document",
        source_url="https://example.com/test.pdf",
        content_hash="abc123def456",
    )


@pytest.fixture
def sample_chunks(sample_document: DocumentNode) -> list[ChunkNode]:
    """Create sample ChunkNodes linked to the sample document."""
    return [
        ChunkNode(
            content="Graph RAG combines vector search with knowledge graphs.",
            chunk_index=0,
            document_id=sample_document.id,
        ),
        ChunkNode(
            content="Neo4j is a graph database that supports Cypher queries.",
            chunk_index=1,
            document_id=sample_document.id,
        ),
        ChunkNode(
            content="Entity extraction uses LLMs to identify named entities.",
            chunk_index=2,
            document_id=sample_document.id,
        ),
    ]


@pytest.fixture
def sample_entity() -> EntityNode:
    """Create a sample EntityNode."""
    return EntityNode(
        name="Neo4j",
        entity_type=EntityType.TECHNOLOGY,
        description="A graph database management system.",
    )


@pytest.fixture
def sample_concept() -> ConceptNode:
    """Create a sample ConceptNode."""
    return ConceptNode(
        name="Graph RAG",
        definition="Retrieval-Augmented Generation using graph databases.",
    )


@pytest.fixture
def sample_relationship(
    sample_document: DocumentNode,
    sample_chunks: list[ChunkNode],
) -> GraphRelationship:
    """Create a sample HAS_CHUNK relationship."""
    return GraphRelationship(
        relation_type=RelationType.HAS_CHUNK,
        source_id=sample_document.id,
        target_id=sample_chunks[0].id,
        weight=1.0,
    )


# ──────────────────────────────────────────
# Mock Service Fixtures
# ──────────────────────────────────────────


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    """Mock EmbeddingService that returns fake 1024-dim vectors."""
    service = MagicMock()
    service.is_loaded = True
    service.dimension = 1024

    fake_vector = [0.1] * 1024
    service.embed_query = AsyncMock(return_value=fake_vector)
    service.embed_documents = AsyncMock(
        side_effect=lambda texts: [fake_vector for _ in texts]
    )
    return service


@pytest.fixture
def mock_graph_store() -> AsyncMock:
    """Mock GraphStore with all async methods."""
    store = AsyncMock()
    store.check_connectivity = AsyncMock(return_value=True)
    store.upsert_nodes = AsyncMock(return_value=3)
    store.upsert_relationships = AsyncMock(return_value=2)
    store.vector_search = AsyncMock(return_value=[])
    store.traverse_from_chunks = AsyncMock(return_value=[])
    store.ensure_indexes = AsyncMock()
    return store
