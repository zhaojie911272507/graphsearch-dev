"""Tests for temporal domain models."""

import pytest
from datetime import datetime
from uuid import uuid4

from app.domain.temporal import (
    EntityVersion,
    RelationshipSnapshot,
    EntitySummary,
    RelationshipSummary,
    GlobalSummary,
)


def test_entity_version_creation():
    """Test EntityVersion can be created with required fields."""
    entity_id = uuid4()
    version = EntityVersion(
        entity_id=entity_id,
        version=1,
        properties={"name": "Test", "description": "Test entity"}
    )

    assert version.id is not None
    assert version.entity_id == entity_id
    assert version.version == 1
    assert version.properties["name"] == "Test"
    assert version.change_summary == ""
    assert version.source_document_ids == []


def test_entity_version_neo4j_properties():
    """Test EntityVersion neo4j_properties method returns correct format."""
    entity_id = uuid4()
    version = EntityVersion(
        entity_id=entity_id,
        version=1,
        properties={"name": "Test"}
    )

    props = version.neo4j_properties()
    assert "id" in props
    assert "entity_id" in props
    assert "version" in props
    assert "timestamp" in props
    assert "properties" in props
    assert props["version"] == 1
    assert props["properties"] == {"name": "Test"}


def test_entity_version_with_all_fields():
    """Test EntityVersion with all optional fields."""
    entity_id = uuid4()
    doc_ids = ["doc1", "doc2"]
    version = EntityVersion(
        entity_id=entity_id,
        version=2,
        properties={"status": "active"},
        change_summary="Updated status",
        source_document_ids=doc_ids
    )

    assert version.change_summary == "Updated status"
    assert version.source_document_ids == doc_ids


def test_relationship_snapshot_creation():
    """Test RelationshipSnapshot can be created with required fields."""
    source_id = uuid4()
    target_id = uuid4()

    snapshot = RelationshipSnapshot(
        source_id=source_id,
        target_id=target_id,
        relation_type="RELATED_TO",
        properties={"description": "Test relationship"},
        weight=0.8
    )

    assert snapshot.id is not None
    assert snapshot.source_id == source_id
    assert snapshot.target_id == target_id
    assert snapshot.relation_type == "RELATED_TO"
    assert snapshot.is_current is True
    assert snapshot.weight == 0.8
    assert snapshot.properties["description"] == "Test relationship"


def test_relationship_snapshot_neo4j_properties():
    """Test RelationshipSnapshot neo4j_properties returns correct format."""
    source_id = uuid4()
    target_id = uuid4()

    snapshot = RelationshipSnapshot(
        source_id=source_id,
        target_id=target_id,
        relation_type="BELONGS_TO",
        weight=0.9
    )

    props = snapshot.neo4j_properties()
    assert "id" in props
    assert "source_id" in props
    assert "target_id" in props
    assert "relation_type" in props
    assert "valid_from" in props
    assert "is_current" in props
    assert props["weight"] == 0.9


def test_relationship_snapshot_with_temporal_fields():
    """Test RelationshipSnapshot with temporal fields."""
    source_id = uuid4()
    target_id = uuid4()
    valid_from = datetime(2024, 1, 1)
    valid_to = datetime(2024, 12, 31)

    snapshot = RelationshipSnapshot(
        source_id=source_id,
        target_id=target_id,
        relation_type="WORKS_AT",
        valid_from=valid_from,
        valid_to=valid_to,
        is_current=False
    )

    assert snapshot.valid_from == valid_from
    assert snapshot.valid_to == valid_to
    assert snapshot.is_current is False


def test_entity_summary_creation():
    """Test EntitySummary can be created."""
    entity_id = uuid4()
    now = datetime.utcnow()

    summary = EntitySummary(
        entity_id=entity_id,
        entity_name="Test Entity",
        entity_type="PERSON",
        current_description="A test entity",
        version_count=5,
        first_seen=now,
        last_updated=now,
        importance_score=0.8
    )

    assert summary.entity_id == entity_id
    assert summary.entity_name == "Test Entity"
    assert summary.version_count == 5
    assert summary.importance_score == 0.8


def test_relationship_summary_creation():
    """Test RelationshipSummary can be created."""
    source_id = uuid4()
    target_id = uuid4()

    summary = RelationshipSummary(
        source_id=source_id,
        target_id=target_id,
        relation_type="RELATED_TO",
        duration_days=30,
        snapshot_count=3,
        strength_trend="rising"
    )

    assert summary.source_id == source_id
    assert summary.target_id == target_id
    assert summary.duration_days == 30
    assert summary.strength_trend == "rising"


def test_global_summary_creation():
    """Test GlobalSummary can be created."""
    summary = GlobalSummary(
        total_entities=100,
        total_versions=500,
        total_snapshots=200,
        top_entities=[
            {"name": "Entity1", "score": 0.9},
            {"name": "Entity2", "score": 0.8}
        ],
        relationship_density=0.75
    )

    assert summary.total_entities == 100
    assert summary.total_versions == 500
    assert len(summary.top_entities) == 2
    assert summary.relationship_density == 0.75


def test_entity_version_frozen():
    """Test that EntityVersion is immutable (frozen)."""
    entity_id = uuid4()
    version = EntityVersion(
        entity_id=entity_id,
        version=1,
        properties={}
    )

    with pytest.raises(Exception):  # pydantic validation error
        version.version = 2


def test_relationship_snapshot_frozen():
    """Test that RelationshipSnapshot is immutable (frozen)."""
    source_id = uuid4()
    target_id = uuid4()
    snapshot = RelationshipSnapshot(
        source_id=source_id,
        target_id=target_id,
        relation_type="RELATED_TO"
    )

    with pytest.raises(Exception):  # pydantic validation error
        snapshot.weight = 0.9