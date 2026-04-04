"""Temporal extractor for incremental extraction and change tracking."""

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from app.domain.nodes import EntityNode
from app.domain.relationships import GraphRelationship
from app.domain.temporal import EntityVersion, RelationshipSnapshot

if TYPE_CHECKING:
    from app.services.temporal_knowledge.batch_merger import BatchMerger
    from app.services.temporal_knowledge.version_manager import VersionManager

logger = logging.getLogger(__name__)


class ChangeSet:
    """Represents detected changes in entity or relationship."""

    def __init__(
        self,
        added_entities: list[EntityNode] | None = None,
        modified_entities: list[tuple[EntityNode, EntityNode]] | None = None,
        deleted_entities: list[UUID] | None = None,
        added_relationships: list[GraphRelationship] | None = None,
        modified_relationships: list[tuple[GraphRelationship, GraphRelationship]] | None = None,
        deleted_relationships: list[str] | None = None,
    ) -> None:
        self.added_entities = added_entities or []
        self.modified_entities = modified_entities or []
        self.deleted_entities = deleted_entities or []
        self.added_relationships = added_relationships or []
        self.modified_relationships = modified_relationships or []
        self.deleted_relationships = deleted_relationships or []

    @property
    def has_changes(self) -> bool:
        return bool(
            self.added_entities
            or self.modified_entities
            or self.deleted_entities
            or self.added_relationships
            or self.modified_relationships
            or self.deleted_relationships
        )

    @property
    def change_count(self) -> int:
        return (
            len(self.added_entities)
            + len(self.modified_entities)
            + len(self.deleted_entities)
            + len(self.added_relationships)
            + len(self.modified_relationships)
            + len(self.deleted_relationships)
        )


class TemporalExtractor:
    """Handles incremental extraction and version management.

    This class is responsible for detecting changes in entities and relationships,
    creating appropriate versions/snapshots, and queuing them for batch processing.
    """

    def __init__(
        self,
        version_manager: "VersionManager",
        batch_merger: "BatchMerger",
        version_threshold: int = 1
    ) -> None:
        """Initialize the temporal extractor.

        Args:
            version_manager: Version manager for creating versions and snapshots.
            batch_merger: Batch merger for queuing items.
            version_threshold: Minimum number of changes required to create a new version.
        """
        self._version_manager = version_manager
        self._batch_merger = batch_merger
        self._version_threshold = version_threshold
        self._entity_cache: dict[str, EntityNode] = {}

    def cache_entity(self, entity: EntityNode) -> None:
        """Cache entity for change detection.

        Args:
            entity: The entity to cache.
        """
        key = self._get_entity_key(entity)
        self._entity_cache[key] = entity

    def get_cached_entity(self, name: str, entity_type: str) -> EntityNode | None:
        """Get cached entity by name and type.

        Args:
            name: Entity name.
            entity_type: Entity type string.

        Returns:
            Cached entity if found, None otherwise.
        """
        key = f"{name}|{entity_type}"
        return self._entity_cache.get(key)

    def _get_entity_key(self, entity: EntityNode) -> str:
        """Generate cache key for entity."""
        return f"{entity.name}|{entity.entity_type.value}"

    def detect_entity_changes(
        self,
        new_entities: list[EntityNode]
    ) -> list[EntityNode]:
        """Detect which entities are new (need version creation).

        Args:
            new_entities: List of new entities to check.

        Returns:
            List of entities that need new versions.
        """
        new_entity_versions = []

        for entity in new_entities:
            key = self._get_entity_key(entity)
            cached = self._entity_cache.get(key)

            if cached is None:
                # New entity
                new_entity_versions.append(entity)
            elif self._has_entity_changes(cached, entity):
                # Modified entity
                new_entity_versions.append(entity)

            # Update cache
            self._entity_cache[key] = entity

        return new_entity_versions

    def _has_entity_changes(self, old: EntityNode, new: EntityNode) -> bool:
        """Check if entity has meaningful changes.

        Args:
            old: Old entity state.
            new: New entity state.

        Returns:
            True if entity has significant changes.
        """
        changes = 0

        if old.description != new.description:
            changes += 1
        if old.name != new.name:
            changes += 1

        return changes >= self._version_threshold

    def detect_relationship_changes(
        self,
        new_relationships: list[GraphRelationship],
        existing_relationships: list[RelationshipSnapshot]
    ) -> list[GraphRelationship]:
        """Detect which relationships need new snapshots.

        Args:
            new_relationships: New relationships to check.
            existing_relationships: Existing relationship snapshots.

        Returns:
            List of relationships that need new snapshots.
        """
        new_snapshots = []

        # Build existing relationship lookup
        existing_map: dict[tuple[str, str], RelationshipSnapshot] = {}
        for rel in existing_relationships:
            key = (str(rel.source_id), str(rel.target_id))
            existing_map[key] = rel

        for rel in new_relationships:
            key = (str(rel.source_id), str(rel.target_id))
            existing = existing_map.get(key)

            if existing is None:
                # New relationship
                new_snapshots.append(rel)
            elif abs(existing.weight - rel.weight) > 0.1:
                # Weight changed significantly
                new_snapshots.append(rel)

        return new_snapshots

    async def process_entity_versions(
        self,
        entities: list[EntityNode],
        timestamp: datetime | None = None
    ) -> list[EntityVersion]:
        """Process entities and create versions.

        Args:
            entities: List of entities to process.
            timestamp: Timestamp for versions. Defaults to current time.

        Returns:
            List of created entity versions.
        """
        timestamp = timestamp or datetime.now(timezone.utc)

        # Detect which entities need new versions
        entities_to_version = self.detect_entity_changes(entities)

        versions = []
        for entity in entities_to_version:
            try:
                version = await self._version_manager.create_entity_version(
                    entity=entity,
                    timestamp=timestamp,
                    change_summary=f"Document processed at {timestamp.isoformat()}"
                )
                versions.append(version)
            except Exception as e:
                logger.error(
                    "Failed to create version for entity %s: %s",
                    entity.id,
                    e
                )

        return versions

    async def process_relationship_snapshots(
        self,
        relationships: list[GraphRelationship],
        timestamp: datetime | None = None
    ) -> list[RelationshipSnapshot]:
        """Process relationships and create snapshots.

        Args:
            relationships: List of relationships to process.
            timestamp: Timestamp for snapshots. Defaults to current time.

        Returns:
            List of created relationship snapshots.
        """
        timestamp = timestamp or datetime.now(timezone.utc)

        snapshots = []

        for rel in relationships:
            try:
                # Check existing relationship
                existing = await self._version_manager.get_current_relationship(
                    rel.source_id,
                    rel.target_id
                )

                # Determine if new snapshot needed
                needs_snapshot = True
                if existing:
                    if abs(existing.weight - rel.weight) <= 0.1:
                        needs_snapshot = False

                if needs_snapshot:
                    snapshot = await self._version_manager.create_relationship_snapshot(
                        source_id=rel.source_id,
                        target_id=rel.target_id,
                        relation_type=rel.relation_type.value,
                        properties={"original_weight": rel.weight},
                        weight=rel.weight,
                        timestamp=timestamp
                    )
                    snapshots.append(snapshot)
            except Exception as e:
                logger.error(
                    "Failed to create snapshot for relationship %s -> %s: %s",
                    rel.source_id,
                    rel.target_id,
                    e
                )

        return snapshots

    async def queue_for_batch(
        self,
        entity_versions: list[EntityVersion],
        relationship_snapshots: list[RelationshipSnapshot],
        document_id: str
    ) -> None:
        """Queue items for batch processing.

        Args:
            entity_versions: Entity versions to queue.
            relationship_snapshots: Relationship snapshots to queue.
            document_id: Document ID associated with these items.
        """
        for version in entity_versions:
            await self._batch_merger.add_to_queue(
                item_type="entity_version",
                data={"version_id": str(version.id)},
                document_id=document_id
            )

        for snapshot in relationship_snapshots:
            await self._batch_merger.add_to_queue(
                item_type="relationship_snapshot",
                data={"snapshot_id": str(snapshot.id)},
                document_id=document_id
            )