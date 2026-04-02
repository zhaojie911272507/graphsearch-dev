"""Tests for version manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from uuid import uuid4

from app.domain.temporal import EntityVersion, RelationshipSnapshot
from app.services.temporal_knowledge.version_manager import VersionManager


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.get_entity_history = AsyncMock(return_value=[])
    store.get_entity_at_time = AsyncMock(return_value=None)
    store.merge_entity_versions = AsyncMock(return_value=1)
    store.merge_relationship_snapshots = AsyncMock(return_value=1)
    store.get_relationship_snapshots = AsyncMock(return_value=[])
    store.get_current_relationship = AsyncMock(return_value=None)
    return store


@pytest.fixture
def version_manager(mock_store):
    return VersionManager(mock_store)


@pytest.mark.asyncio
async def test_create_entity_version(version_manager, mock_store):
    from app.domain.nodes import EntityNode
    from app.domain.enums import EntityType

    entity = EntityNode(
        id=uuid4(),
        name="Test Entity",
        entity_type=EntityType.PERSON,
        description="Test description"
    )

    version = await version_manager.create_entity_version(entity)

    assert version.entity_id == entity.id
    assert version.version == 1
    assert version.properties["name"] == "Test Entity"
    mock_store.merge_entity_versions.assert_called_once()


@pytest.mark.asyncio
async def test_get_entity_history(version_manager, mock_store):
    entity_id = uuid4()

    mock_store.get_entity_history = AsyncMock(return_value=[
        {
            "ev": {
                "id": str(uuid4()),
                "entity_id": str(entity_id),
                "version": 1,
                "timestamp": datetime.utcnow().isoformat(),
                "properties": {"name": "Test"},
                "change_summary": "Initial",
                "source_document_ids": []
            }
        }
    ])

    history = await version_manager.get_entity_history(entity_id)

    assert len(history) == 1
    assert history[0].version == 1


@pytest.mark.asyncio
async def test_get_entity_at_time(version_manager, mock_store):
    entity_id = uuid4()
    test_time = datetime(2024, 1, 15, 10, 0, 0)

    mock_store.get_entity_at_time = AsyncMock(return_value={
        "ev": {
            "id": str(uuid4()),
            "entity_id": str(entity_id),
            "version": 2,
            "timestamp": test_time.isoformat(),
            "properties": {"name": "Updated Entity", "entity_type": "PERSON"},
            "change_summary": "Updated name",
            "source_document_ids": []
        }
    })

    result = await version_manager.get_entity_at_time(entity_id, test_time)

    assert result is not None
    assert result.entity_id == entity_id
    assert result.version == 2
    assert result.properties["name"] == "Updated Entity"
    mock_store.get_entity_at_time.assert_called_once_with(entity_id, test_time)


@pytest.mark.asyncio
async def test_create_relationship_snapshot(version_manager, mock_store):
    source_id = uuid4()
    target_id = uuid4()
    relation_type = "KNOWS"

    snapshot = await version_manager.create_relationship_snapshot(
        source_id=source_id,
        target_id=target_id,
        relation_type=relation_type,
        properties={"context": "work"},
        weight=0.8
    )

    assert snapshot.source_id == source_id
    assert snapshot.target_id == target_id
    assert snapshot.relation_type == relation_type
    assert snapshot.properties["context"] == "work"
    assert snapshot.weight == 0.8
    assert snapshot.is_current is True
    mock_store.merge_relationship_snapshots.assert_called_once()


@pytest.mark.asyncio
async def test_get_relationship_history(version_manager, mock_store):
    source_id = uuid4()
    target_id = uuid4()
    from_time = datetime(2024, 1, 1)
    to_time = datetime(2024, 12, 31)

    mock_store.get_relationship_snapshots = AsyncMock(return_value=[
        {
            "r": {
                "id": str(uuid4()),
                "source_id": str(source_id),
                "target_id": str(target_id),
                "relation_type": "KNOWS",
                "valid_from": "2024-01-01T00:00:00",
                "valid_to": "2024-06-01T00:00:00",
                "properties": {"context": "personal"},
                "weight": 0.5,
                "is_current": False
            }
        },
        {
            "r": {
                "id": str(uuid4()),
                "source_id": str(source_id),
                "target_id": str(target_id),
                "relation_type": "KNOWS",
                "valid_from": "2024-06-01T00:00:00",
                "valid_to": None,
                "properties": {"context": "work"},
                "weight": 0.8,
                "is_current": True
            }
        }
    ])

    history = await version_manager.get_relationship_history(
        source_id, target_id, from_time, to_time
    )

    assert len(history) == 2
    assert history[0].is_current is False
    assert history[1].is_current is True
    assert history[1].properties["context"] == "work"


@pytest.mark.asyncio
async def test_get_current_relationship(version_manager, mock_store):
    source_id = uuid4()
    target_id = uuid4()

    mock_store.get_current_relationship = AsyncMock(return_value={
        "r": {
            "id": str(uuid4()),
            "source_id": str(source_id),
            "target_id": str(target_id),
            "relation_type": "WORKS_WITH",
            "valid_from": "2024-01-01T00:00:00",
            "valid_to": None,
            "properties": {"project": "Alpha"},
            "weight": 0.9,
            "is_current": True
        }
    })

    result = await version_manager.get_current_relationship(source_id, target_id)

    assert result is not None
    assert result.source_id == source_id
    assert result.target_id == target_id
    assert result.relation_type == "WORKS_WITH"
    assert result.properties["project"] == "Alpha"
    assert result.is_current is True
    mock_store.get_current_relationship.assert_called_once_with(source_id, target_id)