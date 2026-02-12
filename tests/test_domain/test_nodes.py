"""Tests for graph node domain models."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from app.domain.enums import EntityType, NodeType
from app.domain.nodes import (
    ChunkNode,
    ConceptNode,
    DocumentNode,
    EntityNode,
    NodeMetadata,
)


class TestNodeMetadata:
    """Tests for NodeMetadata immutability and defaults."""

    def test_metadata_has_defaults(self) -> None:
        meta = NodeMetadata()
        assert meta.source == "system"
        assert meta.tags == ()
        assert meta.created_at is not None

    def test_metadata_is_frozen(self) -> None:
        meta = NodeMetadata()
        with pytest.raises(ValidationError):
            meta.source = "changed"  # type: ignore[misc]


class TestDocumentNode:
    """Tests for DocumentNode creation and serialization."""

    def test_create_document(self) -> None:
        doc = DocumentNode(title="My Report", source_url="https://example.com")
        assert doc.node_type == NodeType.DOCUMENT
        assert isinstance(doc.id, UUID)
        assert doc.title == "My Report"

    def test_document_requires_title(self) -> None:
        with pytest.raises(ValidationError):
            DocumentNode(title="")  # min_length=1

    def test_neo4j_properties(self) -> None:
        doc = DocumentNode(title="Test", content_hash="abc")
        props = doc.neo4j_properties()
        assert props["title"] == "Test"
        assert props["content_hash"] == "abc"
        assert isinstance(props["id"], str)


class TestChunkNode:
    """Tests for ChunkNode with embedding validation."""

    def test_create_chunk_without_embedding(self, sample_document: DocumentNode) -> None:
        chunk = ChunkNode(
            content="Hello world",
            chunk_index=0,
            document_id=sample_document.id,
        )
        assert chunk.embedding == ()

    def test_valid_embedding_dimension(self, sample_document: DocumentNode) -> None:
        vector = tuple([0.1] * 1024)
        chunk = ChunkNode(
            content="Hello world",
            chunk_index=0,
            document_id=sample_document.id,
            embedding=vector,
        )
        assert len(chunk.embedding) == 1024

    def test_invalid_embedding_dimension(self, sample_document: DocumentNode) -> None:
        vector = tuple([0.1] * 512)  # Wrong dimension
        with pytest.raises(ValidationError, match="1024"):
            ChunkNode(
                content="Hello world",
                chunk_index=0,
                document_id=sample_document.id,
                embedding=vector,
            )

    def test_neo4j_properties_include_embedding(self, sample_document: DocumentNode) -> None:
        vector = tuple([0.1] * 1024)
        chunk = ChunkNode(
            content="Test content",
            chunk_index=0,
            document_id=sample_document.id,
            embedding=vector,
        )
        props = chunk.neo4j_properties()
        assert isinstance(props["embedding"], list)
        assert len(props["embedding"]) == 1024


class TestEntityNode:
    """Tests for EntityNode."""

    def test_create_entity(self) -> None:
        entity = EntityNode(
            name="OpenAI",
            entity_type=EntityType.ORGANIZATION,
            description="AI research company",
        )
        assert entity.node_type == NodeType.ENTITY
        assert entity.entity_type == EntityType.ORGANIZATION

    def test_entity_requires_name(self) -> None:
        with pytest.raises(ValidationError):
            EntityNode(name="", entity_type=EntityType.PERSON)


class TestConceptNode:
    """Tests for ConceptNode."""

    def test_create_concept(self) -> None:
        concept = ConceptNode(
            name="Machine Learning",
            definition="A subset of AI focused on learning from data.",
        )
        assert concept.node_type == NodeType.CONCEPT
        assert concept.name == "Machine Learning"
