"""Version management for temporal knowledge graph."""

import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.nodes import EntityNode
from app.domain.temporal import EntityVersion, RelationshipSnapshot
from app.persistence.temporal_store import TemporalStore

logger = logging.getLogger(__name__)


class VersionManager:
    """Manages entity versions and relationship snapshots."""

    def __init__(self, store: TemporalStore) -> None:
        self._store = store

    async def create_entity_version(
        self,
        entity: EntityNode,
        timestamp: datetime | None = None,
        change_summary: str | None = None
    ) -> EntityVersion:
        """Create a new entity version."""
        timestamp = timestamp or datetime.now(timezone.utc)

        # Get current version number
        history = await self._store.get_entity_history(
            entity.id,
            from_time=datetime.min,
            to_time=timestamp
        )
        version_number = len(history) + 1

        version = EntityVersion(
            id=uuid4(),
            entity_id=entity.id,
            version=version_number,
            timestamp=timestamp,
            properties={
                "name": entity.name,
                "entity_type": entity.entity_type.value,
                "description": entity.description,
                "reference_count": entity.reference_count,
            },
            change_summary=change_summary or "",
            source_document_ids=entity.source_document_ids,
        )

        await self._store.merge_entity_versions([version])

        logger.info(
            "Created entity version %d for entity %s",
            version_number,
            entity.id
        )

        return version

    async def get_entity_history(
        self,
        entity_id: UUID,
        from_time: datetime | None = None,
        to_time: datetime | None = None
    ) -> list[EntityVersion]:
        """Get entity version history."""
        records = await self._store.get_entity_history(entity_id, from_time, to_time)

        versions = []
        for record in records:
            ev = record.get("ev", {})
            if ev:
                versions.append(EntityVersion(
                    id=UUID(ev["id"]),
                    entity_id=UUID(ev["entity_id"]),
                    version=ev["version"],
                    timestamp=datetime.fromisoformat(ev["timestamp"]),
                    properties=ev.get("properties", {}),
                    change_summary=ev.get("change_summary", ""),
                    source_document_ids=ev.get("source_document_ids", []),
                ))

        return versions

    async def get_entity_at_time(
        self,
        entity_id: UUID,
        timestamp: datetime
    ) -> EntityVersion | None:
        """Query entity at specific point in time."""
        record = await self._store.get_entity_at_time(entity_id, timestamp)

        if not record:
            return None

        ev = record.get("ev", {})
        if not ev:
            return None

        return EntityVersion(
            id=UUID(ev["id"]),
            entity_id=UUID(ev["entity_id"]),
            version=ev["version"],
            timestamp=datetime.fromisoformat(ev["timestamp"]),
            properties=ev.get("properties", {}),
            change_summary=ev.get("change_summary", ""),
            source_document_ids=ev.get("source_document_ids", []),
        )

    async def create_relationship_snapshot(
        self,
        source_id: UUID,
        target_id: UUID,
        relation_type: str,
        properties: dict | None = None,
        weight: float = 0.5,
        timestamp: datetime | None = None
    ) -> RelationshipSnapshot:
        """Create a new relationship snapshot."""
        timestamp = timestamp or datetime.now(timezone.utc)

        snapshot = RelationshipSnapshot(
            id=uuid4(),
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            valid_from=timestamp,
            valid_to=None,
            properties=properties or {},
            weight=weight,
            is_current=True,
        )

        await self._store.merge_relationship_snapshots([snapshot])

        logger.info(
            "Created relationship snapshot %s -> %s (%s)",
            source_id,
            target_id,
            relation_type
        )

        return snapshot

    async def get_relationship_history(
        self,
        source_id: UUID,
        target_id: UUID,
        from_time: datetime | None = None,
        to_time: datetime | None = None
    ) -> list[RelationshipSnapshot]:
        """Get relationship version history."""
        records = await self._store.get_relationship_snapshots(
            source_id, target_id, from_time, to_time
        )

        snapshots = []
        for record in records:
            r = record.get("r", {})
            if r:
                snapshots.append(RelationshipSnapshot(
                    id=UUID(r["id"]),
                    source_id=UUID(r["source_id"]),
                    target_id=UUID(r["target_id"]),
                    relation_type=r.get("relation_type", "RELATED_TO"),
                    valid_from=datetime.fromisoformat(r["valid_from"]),
                    valid_to=datetime.fromisoformat(r["valid_to"]) if r.get("valid_to") else None,
                    properties=r.get("properties", {}),
                    weight=r.get("weight", 0.5),
                    is_current=r.get("is_current", False),
                ))

        return snapshots

    async def get_current_relationship(
        self,
        source_id: UUID,
        target_id: UUID
    ) -> RelationshipSnapshot | None:
        """Get current relationship state."""
        record = await self._store.get_current_relationship(source_id, target_id)

        if not record:
            return None

        r = record.get("r", {})
        if not r:
            return None

        return RelationshipSnapshot(
            id=UUID(r["id"]),
            source_id=UUID(r["source_id"]),
            target_id=UUID(r["target_id"]),
            relation_type=r.get("relation_type", "RELATED_TO"),
            valid_from=datetime.fromisoformat(r["valid_from"]),
            valid_to=datetime.fromisoformat(r["valid_to"]) if r.get("valid_to") else None,
            properties=r.get("properties", {}),
            weight=r.get("weight", 0.5),
            is_current=r.get("is_current", False),
        )