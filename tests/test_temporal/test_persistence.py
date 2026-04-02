"""Tests for temporal store."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from uuid import uuid4

from app.domain.temporal import EntityVersion, RelationshipSnapshot
from app.persistence.temporal_store import TemporalStore


@pytest.fixture
def mock_driver():
    driver = MagicMock()
    session = AsyncMock()
    driver.session.return_value.__aenter__.return_value = session
    driver.session.return_value.__aexit__.return_value = None
    return driver


@pytest.fixture
def temporal_store(mock_driver):
    return TemporalStore(mock_driver)


def test_entity_version_neo4j_properties():
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


def test_relationship_snapshot_neo4j_properties():
    source_id = uuid4()
    target_id = uuid4()

    snapshot = RelationshipSnapshot(
        source_id=source_id,
        target_id=target_id,
        relation_type="RELATED_TO"
    )

    props = snapshot.neo4j_properties()
    assert props["source_id"] == str(source_id)
    assert props["target_id"] == str(target_id)
    assert props["is_current"] is True


@pytest.mark.asyncio
async def test_merge_entity_versions_empty_list(temporal_store, mock_driver):
    """Test merge_entity_versions returns 0 for empty list."""
    session = mock_driver.session.return_value.__aenter__.return_value
    result = await temporal_store.merge_entity_versions([])
    assert result == 0
    session.run.assert_not_called()


@pytest.mark.asyncio
async def test_merge_entity_versions_success(temporal_store, mock_driver):
    """Test merge_entity_versions succeeds with valid input."""
    session = mock_driver.session.return_value.__aenter__.return_value
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value={"count(ev)": 2})
    session.run = AsyncMock(return_value=mock_result)

    entity_id = uuid4()
    versions = [
        EntityVersion(entity_id=entity_id, version=1, properties={"name": "Test"}),
        EntityVersion(entity_id=entity_id, version=2, properties={"name": "Test2"}),
    ]

    result = await temporal_store.merge_entity_versions(versions)
    assert result == 2
    session.run.assert_called_once()


@pytest.mark.asyncio
async def test_merge_relationship_snapshots_empty_list(temporal_store, mock_driver):
    """Test merge_relationship_snapshots returns 0 for empty list."""
    session = mock_driver.session.return_value.__aenter__.return_value
    result = await temporal_store.merge_relationship_snapshots([])
    assert result == 0
    session.run.assert_not_called()


@pytest.mark.asyncio
async def test_merge_relationship_snapshots_success(temporal_store, mock_driver):
    """Test merge_relationship_snapshots succeeds with valid input."""
    session = mock_driver.session.return_value.__aenter__.return_value
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value={"count(r)": 1})
    session.run = AsyncMock(return_value=mock_result)

    source_id = uuid4()
    target_id = uuid4()
    snapshots = [
        RelationshipSnapshot(
            source_id=source_id,
            target_id=target_id,
            relation_type="RELATED_TO"
        ),
    ]

    result = await temporal_store.merge_relationship_snapshots(snapshots)
    assert result == 1
    # Should be called twice: once for marking previous, once for merging
    assert session.run.call_count == 2


@pytest.mark.asyncio
async def test_get_entity_history(temporal_store, mock_driver):
    """Test get_entity_history returns data."""
    session = mock_driver.session.return_value.__aenter__.return_value
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"id": "test", "version": 1}])
    session.run = AsyncMock(return_value=mock_result)

    entity_id = uuid4()
    result = await temporal_store.get_entity_history(entity_id)
    assert len(result) == 1
    session.run.assert_called_once()


@pytest.mark.asyncio
async def test_get_entity_history_with_time_range(temporal_store, mock_driver):
    """Test get_entity_history with time range."""
    session = mock_driver.session.return_value.__aenter__.return_value
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[])
    session.run = AsyncMock(return_value=mock_result)

    entity_id = uuid4()
    from_time = datetime(2024, 1, 1)
    to_time = datetime(2024, 12, 31)

    result = await temporal_store.get_entity_history(entity_id, from_time, to_time)
    assert result == []
    session.run.assert_called_once()


@pytest.mark.asyncio
async def test_get_entity_at_time(temporal_store, mock_driver):
    """Test get_entity_at_time returns entity at specific time."""
    session = mock_driver.session.return_value.__aenter__.return_value
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value={"id": "test", "version": 1})
    session.run = AsyncMock(return_value=mock_result)

    entity_id = uuid4()
    timestamp = datetime(2024, 6, 15)

    result = await temporal_store.get_entity_at_time(entity_id, timestamp)
    assert result is not None
    assert result["id"] == "test"


@pytest.mark.asyncio
async def test_get_entity_at_time_not_found(temporal_store, mock_driver):
    """Test get_entity_at_time returns None when not found."""
    session = mock_driver.session.return_value.__aenter__.return_value
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=None)
    session.run = AsyncMock(return_value=mock_result)

    entity_id = uuid4()
    timestamp = datetime(2024, 6, 15)

    result = await temporal_store.get_entity_at_time(entity_id, timestamp)
    assert result is None


@pytest.mark.asyncio
async def test_get_relationship_snapshots(temporal_store, mock_driver):
    """Test get_relationship_snapshots returns relationship history."""
    session = mock_driver.session.return_value.__aenter__.return_value
    mock_result = AsyncMock()
    mock_result.data = AsyncMock(return_value=[{"id": "rel1"}])
    session.run = AsyncMock(return_value=mock_result)

    source_id = uuid4()
    target_id = uuid4()

    result = await temporal_store.get_relationship_snapshots(source_id, target_id)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_current_relationship(temporal_store, mock_driver):
    """Test get_current_relationship returns current relationship."""
    session = mock_driver.session.return_value.__aenter__.return_value
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value={"id": "rel1", "is_current": True})
    session.run = AsyncMock(return_value=mock_result)

    source_id = uuid4()
    target_id = uuid4()

    result = await temporal_store.get_current_relationship(source_id, target_id)
    assert result is not None
    assert result["is_current"] is True


@pytest.mark.asyncio
async def test_get_global_stats(temporal_store, mock_driver):
    """Test get_global_stats returns statistics."""
    session = mock_driver.session.return_value.__aenter__.return_value
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value={
        "total_entities": 10,
        "total_versions": 50,
        "total_snapshots": 25
    })
    session.run = AsyncMock(return_value=mock_result)

    result = await temporal_store.get_global_stats()
    assert result["total_entities"] == 10
    assert result["total_versions"] == 50
    assert result["total_snapshots"] == 25


@pytest.mark.asyncio
async def test_get_global_stats_empty(temporal_store, mock_driver):
    """Test get_global_stats returns empty dict when no data."""
    session = mock_driver.session.return_value.__aenter__.return_value
    mock_result = AsyncMock()
    mock_result.single = AsyncMock(return_value=None)
    session.run = AsyncMock(return_value=mock_result)

    result = await temporal_store.get_global_stats()
    assert result == {}