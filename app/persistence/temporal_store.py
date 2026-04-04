"""Temporal data persistence layer for Neo4j."""

import logging
from datetime import datetime
from typing import Self
from uuid import UUID

from neo4j import AsyncDriver

from app.domain.temporal import EntityVersion, RelationshipSnapshot

logger = logging.getLogger(__name__)


_MERGE_ENTITY_VERSION = """
UNWIND $batch AS row
MERGE (ev:EntityVersion {id: row.id})
SET ev.entity_id = row.entity_id,
    ev.version = row.version,
    ev.timestamp = row.timestamp,
    ev.properties = row.properties,
    ev.change_summary = row.change_summary,
    ev.source_document_ids = row.source_document_ids
WITH ev, row
MATCH (e:Entity {id: row.entity_id})
MERGE (ev)-[:HAS_VERSION]->(e)
RETURN count(ev)
"""

_MERGE_RELATIONSHIP_SNAPSHOT = """
UNWIND $batch AS row
MATCH (source:Entity {id: row.source_id})
MATCH (target:Entity {id: row.target_id})
MERGE (source)-[r:RELATES_TO {id: row.id}]->(target)
SET r.relation_type = row.relation_type,
    r.valid_from = row.valid_from,
    r.valid_to = row.valid_to,
    r.properties = row.properties,
    r.weight = row.weight,
    r.is_current = row.is_current
RETURN count(r)
"""

_MARK_PREVIOUS_SNAPSHOT = """
MATCH (source:Entity {id: $source_id})-[r:RELATES_TO]->(target:Entity {id: $target_id})
WHERE r.is_current = true AND r.id <> $current_id
SET r.is_current = false, r.valid_to = $valid_from
RETURN count(r)
"""

_UNWIND_MARK_PREVIOUS = """
UNWIND $batch AS row
MATCH (source:Entity {id: row.source_id})-[r:RELATES_TO]->(target:Entity {id: row.target_id})
WHERE r.is_current = true AND r.id <> row.current_id
SET r.is_current = false, r.valid_to = row.valid_from
RETURN count(r)
"""

_GET_ENTITY_HISTORY = """
MATCH (ev:EntityVersion {entity_id: $entity_id})-[:HAS_VERSION]->(e:Entity)
WHERE ev.timestamp >= $from_time AND ev.timestamp <= $to_time
RETURN ev ORDER BY ev.version DESC
"""

_GET_ENTITY_AT_TIME = """
MATCH (ev:EntityVersion)-[:HAS_VERSION]->(e:Entity {id: $entity_id})
WHERE ev.timestamp <= $timestamp
WITH ev ORDER BY ev.version DESC
LIMIT 1
RETURN ev
"""

_GET_RELATIONSHIP_SNAPSHOTS = """
MATCH (source:Entity {id: $source_id})-[r:RELATES_TO]->(target:Entity {id: $target_id})
WHERE r.valid_from >= $from_time AND (r.valid_to IS NULL OR r.valid_to <= $to_time)
RETURN r ORDER BY r.valid_from DESC
"""

_GET_CURRENT_RELATIONSHIP = """
MATCH (source:Entity {id: $source_id})-[r:RELATES_TO]->(target:Entity {id: $target_id})
WHERE r.is_current = true
RETURN r
"""

_GET_GLOBAL_STATS = """
MATCH (ev:EntityVersion)
OPTIONAL MATCH (ev)-[:HAS_VERSION]->(e:Entity)
OPTIONAL MATCH (source:Entity)-[r:RELATES_TO]->(target:Entity)
WHERE r.is_current = true
RETURN count(DISTINCT e) AS total_entities,
       count(DISTINCT ev) AS total_versions,
       count(DISTINCT r) AS total_snapshots
"""

_CREATE_TEMPORAL_INDEXES = """
CREATE INDEX entity_version_entity_id_idx IF NOT EXISTS
FOR (ev:EntityVersion)
ON (ev.entity_id);

CREATE INDEX entity_version_timestamp_idx IF NOT EXISTS
FOR (ev:EntityVersion)
ON (ev.timestamp);

CREATE INDEX entity_version_version_idx IF NOT EXISTS
FOR (ev:EntityVersion)
ON (ev.version);

CREATE INDEX relationship_snapshot_relation_idx IF NOT EXISTS
FOR (r:RELATES_TO)
ON (r.relation_type);

CREATE INDEX relationship_snapshot_valid_from_idx IF NOT EXISTS
FOR (r:RELATES_TO)
ON (r.valid_from);

CREATE INDEX relationship_snapshot_current_idx IF NOT EXISTS
FOR (r:RELATES_TO)
ON (r.is_current);
"""


class TemporalStore:
    """Temporal data persistence for Neo4j."""

    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    async def close(self) -> None:
        await self._driver.close()

    async def create_indexes(self) -> None:
        """Create temporal indexes."""
        async with self._driver.session() as session:
            await session.run(_CREATE_TEMPORAL_INDEXES)

    async def merge_entity_versions(
        self,
        versions: list[EntityVersion]
    ) -> int:
        """Batch merge entity versions."""
        if not versions:
            return 0

        try:
            batch = [v.neo4j_properties() for v in versions]

            async with self._driver.session() as session:
                result = await session.run(_MERGE_ENTITY_VERSION, batch=batch)
                record = await result.single()
                return record["count(ev)"] if record else 0
        except Exception as e:
            logger.error(
                "Failed to merge entity versions",
                extra={"version_count": len(versions), "error": str(e)},
            )
            raise

    async def merge_relationship_snapshots(
        self,
        snapshots: list[RelationshipSnapshot]
    ) -> int:
        """Batch merge relationship snapshots with previous version marking."""
        if not snapshots:
            return 0

        try:
            async with self._driver.session() as session:
                # Build batch for marking previous snapshots
                mark_batch = [
                    {
                        "source_id": str(s.source_id),
                        "target_id": str(s.target_id),
                        "current_id": str(s.id),
                        "valid_from": s.valid_from.isoformat()
                    }
                    for s in snapshots
                ]

                # Batch mark previous versions as non-current (single query)
                await session.run(_UNWIND_MARK_PREVIOUS, batch=mark_batch)

                # Merge new snapshots in batch
                batch = [s.neo4j_properties() for s in snapshots]
                result = await session.run(_MERGE_RELATIONSHIP_SNAPSHOT, batch=batch)
                record = await result.single()
                count = record["count(r)"] if record else 0

                return count
        except Exception as e:
            logger.error(
                "Failed to merge relationship snapshots",
                extra={"snapshot_count": len(snapshots), "error": str(e)},
            )
            raise

    async def get_entity_history(
        self,
        entity_id: UUID,
        from_time: datetime | None = None,
        to_time: datetime | None = None
    ) -> list[dict]:
        """Get entity version history."""
        from_time = from_time or datetime.min
        to_time = to_time or datetime.max

        try:
            async with self._driver.session() as session:
                result = await session.run(
                    _GET_ENTITY_HISTORY,
                    entity_id=str(entity_id),
                    from_time=from_time.isoformat(),
                    to_time=to_time.isoformat()
                )
                records = await result.data()
                return records
        except Exception as e:
            logger.error(
                "Failed to get entity history",
                extra={"entity_id": str(entity_id), "error": str(e)},
            )
            raise

    async def get_entity_at_time(
        self,
        entity_id: UUID,
        timestamp: datetime
    ) -> dict | None:
        """Query entity at specific point in time (time travel)."""
        try:
            async with self._driver.session() as session:
                result = await session.run(
                    _GET_ENTITY_AT_TIME,
                    entity_id=str(entity_id),
                    timestamp=timestamp.isoformat()
                )
                record = await result.single()
                return dict(record) if record else None
        except Exception as e:
            logger.error(
                "Failed to get entity at time",
                extra={"entity_id": str(entity_id), "timestamp": timestamp.isoformat(), "error": str(e)},
            )
            raise

    async def get_relationship_snapshots(
        self,
        source_id: UUID,
        target_id: UUID,
        from_time: datetime | None = None,
        to_time: datetime | None = None
    ) -> list[dict]:
        """Get relationship history."""
        from_time = from_time or datetime.min
        to_time = to_time or datetime.max

        try:
            async with self._driver.session() as session:
                result = await session.run(
                    _GET_RELATIONSHIP_SNAPSHOTS,
                    source_id=str(source_id),
                    target_id=str(target_id),
                    from_time=from_time.isoformat(),
                    to_time=to_time.isoformat()
                )
                return await result.data()
        except Exception as e:
            logger.error(
                "Failed to get relationship snapshots",
                extra={"source_id": str(source_id), "target_id": str(target_id), "error": str(e)},
            )
            raise

    async def get_current_relationship(
        self,
        source_id: UUID,
        target_id: UUID
    ) -> dict | None:
        """Get current relationship state."""
        try:
            async with self._driver.session() as session:
                result = await session.run(
                    _GET_CURRENT_RELATIONSHIP,
                    source_id=str(source_id),
                    target_id=str(target_id)
                )
                record = await result.single()
                return dict(record) if record else None
        except Exception as e:
            logger.error(
                "Failed to get current relationship",
                extra={"source_id": str(source_id), "target_id": str(target_id), "error": str(e)},
            )
            raise

    async def get_global_stats(self) -> dict:
        """Get global temporal statistics."""
        try:
            async with self._driver.session() as session:
                result = await session.run(_GET_GLOBAL_STATS)
                record = await result.single()
                return dict(record) if record else {}
        except Exception as e:
            logger.error(
                "Failed to get global stats",
                extra={"error": str(e)},
            )
            raise