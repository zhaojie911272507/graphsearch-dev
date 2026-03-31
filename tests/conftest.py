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

    # Entity types
    store.get_entity_types = AsyncMock(return_value=[
        {
            "name": "PERSON",
            "description": "A person",
            "color": "#58a6ff",
            "icon": "user",
            "is_builtin": True,
            "created_at": "2026-03-26T00:00:00Z",
            "updated_at": "2026-03-26T00:00:00Z",
        },
        {
            "name": "CUSTOM_ENTITY",
            "description": "A custom entity",
            "color": "#7ee787",
            "icon": "tag",
            "is_builtin": False,
            "created_at": "2026-03-26T00:00:00Z",
            "updated_at": "2026-03-26T00:00:00Z",
            "extraction_prompt_template": "Extract custom entities...",
        },
    ])
    store.count_entity_instances = AsyncMock(return_value=10)
    store.get_entity_type_by_name = AsyncMock(return_value={
        "name": "CUSTOM_ENTITY",
        "description": "A custom entity",
        "color": "#7ee787",
        "icon": "tag",
        "is_builtin": False,
        "created_at": "2026-03-26T00:00:00Z",
        "updated_at": "2026-03-26T00:00:00Z",
        "extraction_prompt_template": "Extract custom entities...",
    })
    store.create_entity_type = AsyncMock(return_value={
        "name": "NEW_ENTITY",
        "description": "A new entity",
        "color": "#ff7b72",
        "icon": "plus",
        "is_builtin": False,
        "created_at": "2026-03-26T00:00:00Z",
        "updated_at": "2026-03-26T00:00:00Z",
        "extraction_prompt_template": "Extract new entities...",
    })
    store.update_entity_type = AsyncMock(return_value={
        "name": "CUSTOM_ENTITY",
        "description": "Updated description",
        "color": "#7ee787",
        "icon": "tag",
        "is_builtin": False,
        "created_at": "2026-03-26T00:00:00Z",
        "updated_at": "2026-03-26T01:00:00Z",
        "extraction_prompt_template": "Updated template...",
    })
    store.delete_entity_type = AsyncMock(return_value=None)

    # Relation types
    store.get_relation_types = AsyncMock(return_value=[
        {
            "name": "RELATED_TO",
            "description": "Generic relationship",
            "source_types": ["*"],
            "target_types": ["*"],
            "directionality": "DIRECTED",
            "is_builtin": True,
            "properties": [],
            "extraction_prompt": "",
        },
        {
            "name": "OWNS",
            "description": "Ownership relationship",
            "source_types": ["PERSON", "ORG"],
            "target_types": ["ASSET"],
            "directionality": "DIRECTED",
            "is_builtin": False,
            "properties": [{"name": "since", "type": "string"}],
            "extraction_prompt": "Extract ownership relationships...",
        },
    ])
    store.count_relation_instances = AsyncMock(return_value=5)
    store.get_relation_type_by_name = AsyncMock(return_value={
        "name": "OWNS",
        "description": "Ownership relationship",
        "source_types": ["PERSON", "ORG"],
        "target_types": ["ASSET"],
        "directionality": "DIRECTED",
        "is_builtin": False,
        "properties": [{"name": "since", "type": "string"}],
        "extraction_prompt": "Extract ownership relationships...",
    })
    store.create_relation_type = AsyncMock(return_value={
        "name": "USES",
        "description": "Usage relationship",
        "source_types": ["PERSON"],
        "target_types": ["TECHNOLOGY"],
        "directionality": "DIRECTED",
        "is_builtin": False,
        "properties": [{"name": "duration", "type": "string"}],
        "extraction_prompt": "Extract usage relationships...",
    })
    store.update_relation_type = AsyncMock(return_value={
        "name": "OWNS",
        "description": "Updated ownership",
        "source_types": ["PERSON", "ORG"],
        "target_types": ["ASSET"],
        "directionality": "DIRECTED",
        "is_builtin": False,
        "properties": [{"name": "since", "type": "string"}, {"name": "percentage", "type": "number"}],
        "extraction_prompt": "Updated extraction prompt...",
    })
    store.delete_relation_type = AsyncMock(return_value=None)

    # Ontology versions
    store.get_ontology_versions = AsyncMock(return_value=[
        {
            "version": "v2.0.0",
            "created_at": "2026-03-26T01:00:00Z",
            "created_by": "user-1",
            "change_summary": "Added new entity types",
            "changes": [],
            "is_active": True,
        },
        {
            "version": "v1.0.0",
            "created_at": "2026-03-26T00:00:00Z",
            "created_by": "system",
            "change_summary": "Initial version",
            "changes": [],
            "is_active": False,
        },
    ])
    store.get_ontology_version = AsyncMock(return_value={
        "version": "v2.0.0",
        "created_at": "2026-03-26T01:00:00Z",
        "created_by": "user-1",
        "change_summary": "Added new entity types",
        "changes": [],
        "is_active": True,
    })
    store.create_ontology_version = AsyncMock(return_value={
        "version": "v3.0.0",
        "created_at": "2026-03-26T02:00:00Z",
        "created_by": "user-2",
        "change_summary": "Major update",
        "changes": [],
        "is_active": False,
    })
    store.get_ontology_version_diff = AsyncMock(return_value={
        "added_entity_types": ["NewType1", "NewType2"],
        "removed_entity_types": ["OldType"],
        "modified_entity_types": [{"name": "ModifiedType", "change": "description updated"}],
        "added_relation_types": ["NewRelation"],
        "removed_relation_types": ["OldRelation"],
        "modified_relation_types": [{"name": "ModifiedRelation", "change": "properties updated"}],
    })
    store.rollback_ontology_to_version = AsyncMock(return_value=True)

    # Evaluation metrics
    store.get_evaluation_metrics = AsyncMock(return_value={
        "context_relevance": 0.85,
        "faithfulness": 0.90,
        "answer_relevance": 0.88,
        "completeness": 0.82,
    })
    store.get_ablation_study = AsyncMock(return_value={
        "full_model": {"context_relevance": 0.85, "faithfulness": 0.90},
        "without_graph": {"context_relevance": 0.75, "faithfulness": 0.80},
        "without_vectors": {"context_relevance": 0.70, "faithfulness": 0.75},
    })
    store.get_query_evaluations = AsyncMock(return_value=[
        {
            "id": "12345678-1234-5678-1234-567812345678",
            "query": "Test query",
            "context_relevance": 0.85,
            "faithfulness": 0.90,
            "answer_relevance": 0.88,
            "completeness": 0.82,
            "created_at": "2026-03-26T00:00:00Z",
        },
    ])

    # Pipeline configs
    store.get_pipeline_configs = AsyncMock(return_value=[
        {
            "id": "12345678-1234-5678-1234-567812345678",
            "name": "Default Pipeline",
            "description": "Default evaluation pipeline",
            "is_active": True,
            "created_by": "system",
            "created_at": "2026-03-26T00:00:00Z",
            "config": {"chunk_size": 512, "top_k": 10},
        },
    ])
    store.create_pipeline_config = AsyncMock(return_value={
        "id": "12345678-1234-5678-1234-567812345679",
        "name": "New Pipeline",
        "description": "New evaluation pipeline",
        "is_active": False,
        "created_by": "user-1",
        "created_at": "2026-03-26T00:00:00Z",
        "config": {"chunk_size": 512, "top_k": 10},
    })
    store.activate_pipeline_config = AsyncMock(return_value=True)

    # Prompt templates
    store.get_prompt_templates = AsyncMock(return_value=[
        {
            "id": "12345678-1234-5678-1234-567812345678",
            "name": "Extraction Prompt",
            "template_type": "EXTRACTION",
            "content": "Extract entities from text...",
            "variables": [],
            "version": "1.0.0",
            "is_active": True,
            "created_by": "system",
            "created_at": "2026-03-26T00:00:00Z",
            "updated_at": "2026-03-26T00:00:00Z",
        },
    ])
    store.create_prompt_template = AsyncMock(return_value={
        "id": "12345678-1234-5678-1234-567812345679",
        "name": "New Extraction Prompt",
        "template_type": "EXTRACTION",
        "content": "New extraction prompt...",
        "variables": [],
        "version": "1.0.0",
        "is_active": True,
        "created_by": "user-1",
        "created_at": "2026-03-26T00:00:00Z",
        "updated_at": "2026-03-26T00:00:00Z",
    })

    # Metadata/Asset catalog
    store.get_metadata_assets = AsyncMock(return_value={
        "items": [
            {
                "id": "asset-1",
                "name": "Test Asset",
                "asset_type": "DOCUMENT",
                "created_at": "2026-03-26T00:00:00Z",
            },
        ],
        "total": 1,
    })

    # Votes
    store.get_vote = AsyncMock(return_value=None)
    store.create_vote = AsyncMock(return_value={
        "id": "vote-1",
        "vote_type": "APPROVE",
        "comment": "Helpful annotation",
        "created_at": "2026-03-26T00:00:00Z",
    })

    return store


@pytest.fixture
def mock_driver():
    """Mock Neo4j driver."""
    # Create a mock session that supports async context manager protocol
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.run = AsyncMock()

    # Create driver with session method that returns the mock session
    driver = AsyncMock()
    driver.session = MagicMock(return_value=mock_session)
    return driver
