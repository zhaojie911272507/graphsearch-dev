"""Tests for temporal extractor."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.domain.enums import EntityType, RelationType
from app.domain.nodes import EntityNode
from app.domain.relationships import GraphRelationship
from app.domain.temporal import EntityVersion, RelationshipSnapshot
from app.services.temporal_knowledge.temporal_extractor import (
    TemporalExtractor,
    ChangeSet,
)


@pytest.fixture
def mock_version_manager():
    """Create a mock version manager."""
    manager = MagicMock()
    manager.create_entity_version = AsyncMock()
    manager.create_relationship_snapshot = AsyncMock()
    manager.get_current_relationship = AsyncMock(return_value=None)
    return manager


@pytest.fixture
def mock_batch_merger():
    """Create a mock batch merger."""
    merger = MagicMock()
    merger.add_to_queue = AsyncMock()
    return merger


@pytest.fixture
def extractor(mock_version_manager, mock_batch_merger):
    """Create a temporal extractor instance."""
    return TemporalExtractor(
        version_manager=mock_version_manager,
        batch_merger=mock_batch_merger,
        version_threshold=1
    )


class TestChangeSet:
    """Tests for ChangeSet class."""

    def test_empty_changeset(self):
        """Test empty changeset has no changes."""
        change_set = ChangeSet()
        assert not change_set.has_changes
        assert change_set.change_count == 0

    def test_added_entities(self):
        """Test changeset with added entities."""
        entity = EntityNode(
            name="Test Entity",
            entity_type=EntityType.PERSON,
            description="Test description"
        )
        change_set = ChangeSet(added_entities=[entity])
        assert change_set.has_changes
        assert change_set.change_count == 1
        assert len(change_set.added_entities) == 1

    def test_modified_entities(self):
        """Test changeset with modified entities."""
        old_entity = EntityNode(
            name="Test Entity",
            entity_type=EntityType.PERSON,
            description="Old description"
        )
        new_entity = EntityNode(
            name="Test Entity",
            entity_type=EntityType.PERSON,
            description="New description"
        )
        change_set = ChangeSet(modified_entities=[(old_entity, new_entity)])
        assert change_set.has_changes
        assert change_set.change_count == 1

    def test_deleted_entities(self):
        """Test changeset with deleted entities."""
        entity_id = uuid4()
        change_set = ChangeSet(deleted_entities=[entity_id])
        assert change_set.has_changes
        assert change_set.change_count == 1

    def test_added_relationships(self):
        """Test changeset with added relationships."""
        rel = GraphRelationship(
            relation_type=RelationType.RELATED_TO,
            source_id=uuid4(),
            target_id=uuid4(),
            weight=0.8
        )
        change_set = ChangeSet(added_relationships=[rel])
        assert change_set.has_changes
        assert change_set.change_count == 1

    def test_mixed_changes(self):
        """Test changeset with multiple types of changes."""
        entity = EntityNode(
            name="Test Entity",
            entity_type=EntityType.PERSON
        )
        rel = GraphRelationship(
            relation_type=RelationType.RELATED_TO,
            source_id=uuid4(),
            target_id=uuid4()
        )
        change_set = ChangeSet(
            added_entities=[entity],
            added_relationships=[rel]
        )
        assert change_set.has_changes
        assert change_set.change_count == 2


class TestTemporalExtractor:
    """Tests for TemporalExtractor class."""

    def test_init(self, extractor, mock_version_manager, mock_batch_merger):
        """Test extractor initialization."""
        assert extractor._version_manager is mock_version_manager
        assert extractor._batch_merger is mock_batch_merger
        assert extractor._version_threshold == 1
        assert extractor._entity_cache == {}

    def test_cache_entity(self, extractor):
        """Test caching an entity."""
        entity = EntityNode(
            name="Test Entity",
            entity_type=EntityType.PERSON,
            description="Test description"
        )
        extractor.cache_entity(entity)

        cached = extractor.get_cached_entity("Test Entity", EntityType.PERSON.value)
        assert cached is not None
        assert cached.name == "Test Entity"

    def test_get_cached_entity_not_found(self, extractor):
        """Test getting a non-existent cached entity."""
        result = extractor.get_cached_entity("NonExistent", EntityType.PERSON.value)
        assert result is None

    def test_detect_entity_changes_new_entity(self, extractor):
        """Test detecting new entity."""
        entity = EntityNode(
            name="New Entity",
            entity_type=EntityType.ORGANIZATION,
            description="A new entity"
        )
        new_entities = [entity]

        result = extractor.detect_entity_changes(new_entities)

        assert len(result) == 1
        assert result[0].name == "New Entity"

    def test_detect_entity_changes_existing(self, extractor):
        """Test detecting changes in existing entity."""
        # First, cache an entity
        existing = EntityNode(
            name="Test Entity",
            entity_type=EntityType.PERSON,
            description="Original description"
        )
        extractor.cache_entity(existing)

        # Now check with same entity - no changes
        new_entities = [existing]
        result = extractor.detect_entity_changes(new_entities)

        # With version_threshold=1 and same description, no new version needed
        assert len(result) == 0

    def test_detect_entity_changes_modified(self, extractor):
        """Test detecting modified entity."""
        # First, cache an entity
        old_entity = EntityNode(
            name="Test Entity",
            entity_type=EntityType.PERSON,
            description="Old description"
        )
        extractor.cache_entity(old_entity)

        # Now check with modified entity
        new_entity = EntityNode(
            name="Test Entity",
            entity_type=EntityType.PERSON,
            description="New description"
        )
        result = extractor.detect_entity_changes([new_entity])

        # Should detect change due to description difference
        assert len(result) == 1
        assert result[0].description == "New description"

    def test_detect_relationship_changes_new(self, extractor):
        """Test detecting new relationship."""
        new_rel = GraphRelationship(
            relation_type=RelationType.RELATED_TO,
            source_id=uuid4(),
            target_id=uuid4(),
            weight=0.8
        )

        result = extractor.detect_relationship_changes(
            [new_rel],
            []
        )

        assert len(result) == 1
        assert result[0] is new_rel

    def test_detect_relationship_changes_existing(self, extractor):
        """Test detecting unchanged relationship."""
        source_id = uuid4()
        target_id = uuid4()

        existing_rel = RelationshipSnapshot(
            source_id=source_id,
            target_id=target_id,
            relation_type="RELATED_TO",
            weight=0.8,
            is_current=True
        )

        new_rel = GraphRelationship(
            relation_type=RelationType.RELATED_TO,
            source_id=source_id,
            target_id=target_id,
            weight=0.85  # Small change, below threshold
        )

        result = extractor.detect_relationship_changes(
            [new_rel],
            [existing_rel]
        )

        # Weight change < 0.1, should not create new snapshot
        assert len(result) == 0

    def test_detect_relationship_changes_modified(self, extractor):
        """Test detecting modified relationship."""
        source_id = uuid4()
        target_id = uuid4()

        existing_rel = RelationshipSnapshot(
            source_id=source_id,
            target_id=target_id,
            relation_type="RELATED_TO",
            weight=0.5,
            is_current=True
        )

        new_rel = GraphRelationship(
            relation_type=RelationType.RELATED_TO,
            source_id=source_id,
            target_id=target_id,
            weight=0.8  # Significant change > 0.1
        )

        result = extractor.detect_relationship_changes(
            [new_rel],
            [existing_rel]
        )

        # Weight change > 0.1, should create new snapshot
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_process_entity_versions(self, extractor, mock_version_manager):
        """Test processing entity versions."""
        entity = EntityNode(
            name="Test Entity",
            entity_type=EntityType.PERSON,
            description="Test description"
        )

        mock_version_manager.create_entity_version.return_value = EntityVersion(
            entity_id=entity.id,
            version=1,
            properties={"name": entity.name}
        )

        timestamp = datetime.now(timezone.utc)
        result = await extractor.process_entity_versions([entity], timestamp)

        assert len(result) == 1
        mock_version_manager.create_entity_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_relationship_snapshots(self, extractor, mock_version_manager):
        """Test processing relationship snapshots."""
        source_id = uuid4()
        target_id = uuid4()

        rel = GraphRelationship(
            relation_type=RelationType.RELATED_TO,
            source_id=source_id,
            target_id=target_id,
            weight=0.8
        )

        mock_version_manager.get_current_relationship.return_value = None
        mock_version_manager.create_relationship_snapshot.return_value = RelationshipSnapshot(
            source_id=source_id,
            target_id=target_id,
            relation_type="RELATED_TO",
            weight=0.8
        )

        timestamp = datetime.now(timezone.utc)
        result = await extractor.process_relationship_snapshots([rel], timestamp)

        assert len(result) == 1
        mock_version_manager.create_relationship_snapshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_queue_for_batch(self, extractor, mock_batch_merger):
        """Test queuing items for batch processing."""
        entity_version = EntityVersion(
            entity_id=uuid4(),
            version=1,
            properties={}
        )

        relationship_snapshot = RelationshipSnapshot(
            source_id=uuid4(),
            target_id=uuid4(),
            relation_type="RELATED_TO",
            weight=0.5
        )

        document_id = "doc-123"

        await extractor.queue_for_batch(
            [entity_version],
            [relationship_snapshot],
            document_id
        )

        assert mock_batch_merger.add_to_queue.call_count == 2

    def test_version_threshold(self, mock_version_manager, mock_batch_merger):
        """Test version threshold configuration."""
        extractor = TemporalExtractor(
            version_manager=mock_version_manager,
            batch_merger=mock_batch_merger,
            version_threshold=2
        )

        # Cache entity
        old_entity = EntityNode(
            name="Test",
            entity_type=EntityType.PERSON,
            description="A"
        )
        extractor.cache_entity(old_entity)

        # One change should not trigger new version
        new_entity = EntityNode(
            name="Test",
            entity_type=EntityType.PERSON,
            description="B"  # One change
        )
        result = extractor.detect_entity_changes([new_entity])
        assert len(result) == 0