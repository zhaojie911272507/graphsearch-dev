# 时序知识图谱实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标:** 构建完整的时序知识图谱系统，支持实体/关系的版本追踪、时间旅行查询和三级摘要生成

**架构:** 采用版本节点 + 关系快照模式，通过增量处理和定时批量合并实现时序数据的持久化和查询

**技术栈:** FastAPI, Neo4j, Pydantic, asyncio, OpenAI

---

## 文件结构

```
app/
├── domain/
│   └── temporal.py              # 新增：时序领域模型
├── persistence/
│   └── temporal_store.py        # 新增：时序数据持久化层
├── services/
│   └── temporal_knowledge/
│       ├── __init__.py
│       ├── temporal_extractor.py    # 增量提取和变更检测
│       ├── version_manager.py        # 版本管理
│       ├── summary_generator.py      # 摘要生成
│       └── batch_merger.py           # 定时批量合并
└── api/
    └── routes/
        └── temporal.py            # 新增：时序查询 API
```

---

### Task 1: 时序领域模型

**Files:**
- Create: `app/domain/temporal.py`
- Modify: `app/domain/enums.py:10-18`
- Test: `tests/test_temporal/test_domain.py`

- [ ] **Step 1: 添加 NodeType 枚举值**

修改 `app/domain/enums.py` 添加 `ENTITY_VERSION`:

```python
class NodeType(StrEnum):
    """Graph node labels matching the Neo4j schema."""

    DOCUMENT = "Document"
    CHUNK = "Chunk"
    ENTITY = "Entity"
    CONCEPT = "Concept"
    ENTITY_VERSION = "EntityVersion"  # 新增
```

- [ ] **Step 2: 创建时序领域模型**

创建 `app/domain/temporal.py`:

```python
"""Temporal knowledge graph domain models."""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import NodeType


class TemporalMetadata(BaseModel):
    """Extensible metadata for temporal nodes."""

    model_config = ConfigDict(frozen=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(default="system")


class EntityVersion(BaseModel):
    """实体版本快照 - 存储实体在特定时间点的状态"""
    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    entity_id: UUID = Field(..., description="关联的主实体 ID")
    version: int = Field(..., ge=1, description="版本号递增")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    properties: dict = Field(default_factory=dict, description="快照时的完整属性")
    change_summary: str = Field(default="", description="变更摘要")
    source_document_ids: list[str] = Field(default_factory=list)

    def neo4j_properties(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "entity_id": str(self.entity_id),
            "version": self.version,
            "timestamp": self.timestamp.isoformat(),
            "properties": self.properties,
            "change_summary": self.change_summary,
            "source_document_ids": self.source_document_ids,
        }


class RelationshipSnapshot(BaseModel):
    """关系快照 - 记录关系在特定时间区间的状态"""
    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    source_id: UUID = Field(...)
    target_id: UUID = Field(...)
    relation_type: str = Field(...)
    valid_from: datetime = Field(default_factory=datetime.utcnow)
    valid_to: datetime | None = Field(default=None)
    properties: dict = Field(default_factory=dict)
    weight: float = Field(default=0.5, ge=0.0, le=1.0)
    is_current: bool = Field(default=True)

    def neo4j_properties(self) -> dict[str, object]:
        return {
            "id": str(self.id),
            "source_id": str(self.source_id),
            "target_id": str(self.target_id),
            "relation_type": self.relation_type,
            "valid_from": self.valid_from.isoformat(),
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "properties": self.properties,
            "weight": self.weight,
            "is_current": self.is_current,
        }


class EntitySummary(BaseModel):
    """实体级摘要"""
    entity_id: UUID
    entity_name: str
    entity_type: str
    current_description: str
    version_count: int
    first_seen: datetime
    last_updated: datetime
    change_history: list[dict]
    importance_score: float = Field(ge=0.0, le=1.0)


class RelationshipSummary(BaseModel):
    """关系级摘要"""
    source_id: UUID
    target_id: UUID
    relation_type: str
    duration_days: int
    snapshot_count: int
    strength_trend: str  # "rising", "declining", "stable"
    key_events: list[dict]


class GlobalSummary(BaseModel):
    """全局级摘要"""
    generated_at: datetime
    total_entities: int
    total_versions: int
    total_snapshots: int
    top_entities: list[dict]
    entity_trend: dict  # {"added": N, "modified": N}
    relationship_density: float
```

- [ ] **Step 3: 编写测试**

创建 `tests/test_temporal/__init__.py` 和 `tests/test_temporal/test_domain.py`:

```python
"""Tests for temporal domain models."""

import pytest
from datetime import datetime
from uuid import uuid4

from app.domain.temporal import EntityVersion, RelationshipSnapshot, EntitySummary


def test_entity_version_creation():
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
    assert version.is_current is True or hasattr(version, 'is_current')


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
    assert props["version"] == 1


def test_relationship_snapshot_creation():
    source_id = uuid4()
    target_id = uuid4()
    
    snapshot = RelationshipSnapshot(
        source_id=source_id,
        target_id=target_id,
        relation_type="RELATED_TO",
        properties={"weight": 0.8}
    )
    
    assert snapshot.id is not None
    assert snapshot.source_id == source_id
    assert snapshot.is_current is True
```

- [ ] **Step 4: 运行测试验证**

Run: `pytest tests/test_temporal/test_domain.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add app/domain/enums.py app/domain/temporal.py tests/test_temporal/
git commit -m "feat: add temporal domain models"

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

---

### Task 2: 时序持久化层

**Files:**
- Create: `app/persistence/temporal_store.py`
- Test: `tests/test_temporal/test_persistence.py`

- [ ] **Step 1: 创建时序持久化层**

创建 `app/persistence/temporal_store.py`:

```python
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
        
        batch = [v.neo4j_properties() for v in versions]
        
        async with self._driver.session() as session:
            result = await session.run(_MERGE_ENTITY_VERSION, batch=batch)
            record = await result.single()
            return record["count(ev)"] if record else 0

    async def merge_relationship_snapshots(
        self,
        snapshots: list[RelationshipSnapshot]
    ) -> int:
        """Batch merge relationship snapshots with previous version marking."""
        if not snapshots:
            return 0
        
        async with self._driver.session() as session:
            count = 0
            for snapshot in snapshots:
                # Mark previous version as non-current
                await session.run(
                    _MARK_PREVIOUS_SNAPSHOT,
                    source_id=str(snapshot.source_id),
                    target_id=str(snapshot.target_id),
                    current_id=str(snapshot.id),
                    valid_from=snapshot.valid_from.isoformat()
                )
            
            # Merge new snapshots
            batch = [s.neo4j_properties() for s in snapshots]
            result = await session.run(_MERGE_RELATIONSHIP_SNAPSHOT, batch=batch)
            record = await result.single()
            count = record["count(r)"] if record else 0
            
            return count

    async def get_entity_history(
        self,
        entity_id: UUID,
        from_time: datetime | None = None,
        to_time: datetime | None = None
    ) -> list[dict]:
        """Get entity version history."""
        from_time = from_time or datetime.min
        to_time = to_time or datetime.max
        
        async with self._driver.session() as session:
            result = await session.run(
                _GET_ENTITY_HISTORY,
                entity_id=str(entity_id),
                from_time=from_time.isoformat(),
                to_time=to_time.isoformat()
            )
            records = await result.data()
            return records

    async def get_entity_at_time(
        self,
        entity_id: UUID,
        timestamp: datetime
    ) -> dict | None:
        """Query entity at specific point in time (time travel)."""
        async with self._driver.session() as session:
            result = await session.run(
                _GET_ENTITY_AT_TIME,
                entity_id=str(entity_id),
                timestamp=timestamp.isoformat()
            )
            record = await result.single()
            return dict(record) if record else None

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
        
        async with self._driver.session() as session:
            result = await session.run(
                _GET_RELATIONSHIP_SNAPSHOTS,
                source_id=str(source_id),
                target_id=str(target_id),
                from_time=from_time.isoformat(),
                to_time=to_time.isoformat()
            )
            return await result.data()

    async def get_current_relationship(
        self,
        source_id: UUID,
        target_id: UUID
    ) -> dict | None:
        """Get current relationship state."""
        async with self._driver.session() as session:
            result = await session.run(
                _GET_CURRENT_RELATIONSHIP,
                source_id=str(source_id),
                target_id=str(target_id)
            )
            record = await result.single()
            return dict(record) if record else None

    async def get_global_stats(self) -> dict:
        """Get global temporal statistics."""
        async with self._driver.session() as session:
            result = await session.run(_GET_GLOBAL_STATS)
            record = await result.single()
            return dict(record) if record else {}
```

- [ ] **Step 2: 编写测试**

创建 `tests/test_temporal/test_persistence.py`:

```python
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
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/test_temporal/test_persistence.py -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add app/persistence/temporal_store.py tests/test_temporal/
git commit -m "feat: add temporal persistence layer"

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

---

### Task 3: 版本管理器

**Files:**
- Create: `app/services/temporal_knowledge/__init__.py`
- Create: `app/services/temporal_knowledge/version_manager.py`
- Test: `tests/test_temporal/test_version_manager.py`

- [ ] **Step 1: 创建版本管理器模块**

创建 `app/services/temporal_knowledge/__init__.py`:

```python
"""Temporal knowledge service."""

from app.services.temporal_knowledge.version_manager import VersionManager
from app.services.temporal_knowledge.summary_generator import SummaryGenerator
from app.services.temporal_knowledge.batch_merger import BatchMerger

__all__ = ["VersionManager", "SummaryGenerator", "BatchMerger"]
```

- [ ] **Step 2: 创建 VersionManager**

创建 `app/services/temporal_knowledge/version_manager.py`:

```python
"""Version management for temporal knowledge graph."""

import logging
from datetime import datetime
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
        timestamp = timestamp or datetime.utcnow()
        
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
        timestamp = timestamp or datetime.utcnow()
        
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
```

- [ ] **Step 3: 编写测试**

创建 `tests/test_temporal/test_version_manager.py`:

```python
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
```

- [ ] **Step 4: 运行测试验证**

Run: `pytest tests/test_temporal/test_version_manager.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add app/services/temporal_knowledge/ tests/test_temporal/
git commit -m "feat: add version manager"

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

---

### Task 4: 摘要生成器

**Files:**
- Create: `app/services/temporal_knowledge/summary_generator.py`
- Modify: `app/config.py:147-161` - 添加 TemporalSettings
- Test: `tests/test_temporal/test_summary_generator.py`

- [ ] **Step 1: 添加配置**

修改 `app/config.py` 在 `Settings` 类中添加 `temporal` 字段:

```python
class TemporalSettings(BaseSettings):
    """Temporal knowledge graph configuration."""
    
    model_config = SettingsConfigDict(env_prefix="TEMPORAL_", env_file=".env", extra="ignore")
    
    batch_interval_minutes: int = Field(default=5, ge=1, le=60)
    version_threshold: int = Field(default=1, ge=1, description="Changes >= N create new version")
    summary_enabled: bool = Field(default=True)


class Settings(BaseSettings):
    # ... existing fields ...
    temporal: TemporalSettings = Field(default_factory=TemporalSettings)
```

- [ ] **Step 2: 创建摘要生成器**

创建 `app/services/temporal_knowledge/summary_generator.py`:

```python
"""Summary generation for temporal knowledge graph."""

import logging
from datetime import datetime
from uuid import UUID

from langchain_openai import ChatOpenAI

from app.config import OpenAISettings, TemporalSettings
from app.domain.temporal import EntitySummary, RelationshipSummary, GlobalSummary
from app.services.temporal_knowledge.version_manager import VersionManager
from app.persistence.temporal_store import TemporalStore

logger = logging.getLogger(__name__)


# Summary generation prompts
ENTITY_SUMMARY_PROMPT = """你是一个知识图谱分析助手。请根据实体的版本历史生成简洁的摘要。

实体名称: {entity_name}
实体类型: {entity_type}
版本数量: {version_count}

版本历史:
{version_history}

请生成:
1. 当前描述（一句话）
2. 最重要的变更（最多3条）
3. 重要性评分（0-1）

格式:
描述: ...
变更: - ... - ... - ...
评分: 0.XX
"""

RELATIONSHIP_SUMMARY_PROMPT = """你是一个关系分析助手。请根据关系的历史快照生成摘要。

源实体: {source_name}
目标实体: {target_name}
关系类型: {relation_type}
快照数量: {snapshot_count}

历史快照:
{snapshots}

请生成:
1. 关系强度趋势（上升/下降/稳定）
2. 关键事件（最多2条）
3. 持续时间

格式:
趋势: ...
事件: - ... - ...
时长: N天
"""

GLOBAL_SUMMARY_PROMPT = """你是一个图谱分析助手。请根据全局统计生成摘要。

实体总数: {total_entities}
版本总数: {total_versions}
快照总数: {total_snapshots}

热点实体:
{top_entities}

趋势数据:
{trends}

请生成:
1. 图谱主题（一句话）
2. 热点领域
3. 发展趋势

格式:
主题: ...
领域: - ... - ...
趋势: ...
"""


class SummaryGenerator:
    """Generates three-level summaries for temporal knowledge graph."""

    def __init__(
        self,
        openai_settings: OpenAISettings,
        temporal_settings: TemporalSettings,
    ) -> None:
        if not openai_settings.api_key:
            raise ValueError("OpenAI API key required for summary generation")
        
        self._llm = ChatOpenAI(
            api_key=openai_settings.api_key,
            base_url=openai_settings.base_url,
            model=openai_settings.model,
            temperature=0.3,
        )
        self._temporal_settings = temporal_settings
        self._version_manager = None  # Set via set_version_manager
        self._temporal_store = None   # Set via set_temporal_store

    def set_version_manager(self, version_manager: VersionManager) -> None:
        self._version_manager = version_manager

    def set_temporal_store(self, temporal_store: TemporalStore) -> None:
        self._temporal_store = temporal_store

    async def generate_entity_summary(
        self,
        entity_id: UUID,
        entity_name: str,
        entity_type: str
    ) -> EntitySummary:
        """Generate entity-level summary."""
        if not self._version_manager:
            raise RuntimeError("Version manager not set")
        
        # Get entity history
        history = await self._version_manager.get_entity_history(entity_id)
        
        if not history:
            return EntitySummary(
                entity_id=entity_id,
                entity_name=entity_name,
                entity_type=entity_type,
                current_description="",
                version_count=0,
                first_seen=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                change_history=[],
                importance_score=0.0
            )
        
        # Build version history text
        version_history = "\n".join([
            f"v{ev.version} ({ev.timestamp.date()}): {ev.change_summary or '无变更'}"
            for ev in reversed(history)
        ])
        
        # Generate LLM summary if enabled
        current_description = history[0].properties.get("description", "")
        importance_score = min(1.0, len(history) / 10.0)  # Simple heuristic
        
        if self._temporal_settings.summary_enabled:
            try:
                prompt = ENTITY_SUMMARY_PROMPT.format(
                    entity_name=entity_name,
                    entity_type=entity_type,
                    version_count=len(history),
                    version_history=version_history
                )
                
                response = await self._llm.ainvoke(prompt)
                content = response.content
                
                # Parse response
                lines = content.split("\n")
                for line in lines:
                    if line.startswith("评分:"):
                        try:
                            importance_score = float(line.split(":")[1].strip())
                        except:
                            pass
            except Exception as e:
                logger.warning("Failed to generate LLM summary: %s", e)
        
        # Build change history
        change_history = [
            {
                "version": ev.version,
                "timestamp": ev.timestamp.isoformat(),
                "summary": ev.change_summary
            }
            for ev in history if ev.change_summary
        ]
        
        return EntitySummary(
            entity_id=entity_id,
            entity_name=entity_name,
            entity_type=entity_type,
            current_description=current_description,
            version_count=len(history),
            first_seen=history[-1].timestamp if history else datetime.utcnow(),
            last_updated=history[0].timestamp if history else datetime.utcnow(),
            change_history=change_history,
            importance_score=importance_score
        )

    async def generate_relationship_summary(
        self,
        source_id: UUID,
        target_id: UUID,
        source_name: str,
        target_name: str,
        relation_type: str
    ) -> RelationshipSummary:
        """Generate relationship-level summary."""
        if not self._version_manager:
            raise RuntimeError("Version manager not set")
        
        # Get relationship history
        snapshots = await self._version_manager.get_relationship_history(
            source_id, target_id
        )
        
        if not snapshots:
            return RelationshipSummary(
                source_id=source_id,
                target_id=target_id,
                relation_type=relation_type,
                duration_days=0,
                snapshot_count=0,
                strength_trend="stable",
                key_events=[]
            )
        
        # Calculate trend
        if len(snapshots) >= 2:
            weights = [s.weight for s in snapshots]
            if weights[0] > weights[-1] + 0.2:
                strength_trend = "rising"
            elif weights[0] < weights[-1] - 0.2:
                strength_trend = "declining"
            else:
                strength_trend = "stable"
        else:
            strength_trend = "stable"
        
        # Calculate duration
        first = snapshots[-1].valid_from
        last = snapshots[0].valid_from
        duration_days = (last - first).days
        
        # Key events
        key_events = [
            {
                "timestamp": s.valid_from.isoformat(),
                "weight": s.weight,
                "properties": s.properties
            }
            for s in snapshots[:2]  # Last 2 snapshots
        ]
        
        return RelationshipSummary(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            duration_days=duration_days,
            snapshot_count=len(snapshots),
            strength_trend=strength_trend,
            key_events=key_events
        )

    async def generate_global_summary(
        self,
        time_range: tuple[datetime, datetime] | None = None
    ) -> GlobalSummary:
        """Generate global-level summary."""
        if not self._temporal_store:
            raise RuntimeError("Temporal store not set")
        
        # Get global stats
        stats = await self._temporal_store.get_global_stats()
        
        return GlobalSummary(
            generated_at=datetime.utcnow(),
            total_entities=stats.get("total_entities", 0),
            total_versions=stats.get("total_versions", 0),
            total_snapshots=stats.get("total_snapshots", 0),
            top_entities=[],  # TODO: Implement top entities query
            entity_trend={"added": 0, "modified": 0},  # TODO: Implement trend
            relationship_density=0.0  # TODO: Implement density calculation
        )
```

- [ ] **Step 3: 编写测试**

创建 `tests/test_temporal/test_summary_generator.py`:

```python
"""Tests for summary generator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4

from app.config import OpenAISettings, TemporalSettings
from app.services.temporal_knowledge.summary_generator import SummaryGenerator


@pytest.fixture
def openai_settings():
    return OpenAISettings(api_key="test-key")


@pytest.fixture
def temporal_settings():
    return TemporalSettings(summary_enabled=False)


@pytest.fixture
def summary_generator(openai_settings, temporal_settings):
    with patch("langchain_openai.ChatOpenAI"):
        generator = SummaryGenerator(openai_settings, temporal_settings)
        return generator


def test_summary_generator_initialization(summary_generator):
    assert summary_generator is not None


def test_set_version_manager(summary_generator):
    mock_manager = MagicMock()
    summary_generator.set_version_manager(mock_manager)
    assert summary_generator._version_manager == mock_manager


def test_set_temporal_store(summary_generator):
    mock_store = MagicMock()
    summary_generator.set_temporal_store(mock_store)
    assert summary_generator._temporal_store == mock_store


@pytest.mark.asyncio
async def test_generate_entity_summary_without_manager(summary_generator):
    with pytest.raises(RuntimeError, match="Version manager not set"):
        await summary_generator.generate_entity_summary(
            uuid4(), "Test", "PERSON"
        )
```

- [ ] **Step 4: 运行测试验证**

Run: `pytest tests/test_temporal/test_summary_generator.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add app/config.py app/services/temporal_knowledge/summary_generator.py tests/test_temporal/
git commit -m "feat: add summary generator"

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

---

### Task 5: 定时批量合并器

**Files:**
- Create: `app/services/temporal_knowledge/batch_merger.py`
- Test: `tests/test_temporal/test_batch_merger.py`

- [ ] **Step 1: 创建批量合并器**

创建 `app/services/temporal_knowledge/batch_merger.py`:

```python
"""Batch merger for temporal knowledge graph."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from app.config import TemporalSettings

logger = logging.getLogger(__name__)


class PendingItem:
    """Pending item for batch processing."""

    def __init__(
        self,
        item_type: str,
        data: dict[str, Any],
        document_id: str
    ) -> None:
        self.item_type = item_type  # "entity_version" or "relationship_snapshot"
        self.data = data
        self.document_id = document_id
        self.created_at = datetime.utcnow()


class BatchMerger:
    """Handles batch merging of temporal data with scheduled execution."""

    def __init__(
        self,
        temporal_settings: TemporalSettings,
        version_manager: "VersionManager | None" = None,
        summary_generator: "SummaryGenerator | None" = None
    ) -> None:
        self._settings = temporal_settings
        self._version_manager = version_manager
        self._summary_generator = summary_generator
        self._queue: asyncio.Queue[PendingItem] = asyncio.Queue()
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_merge_time: datetime | None = None

    def set_version_manager(self, version_manager: "VersionManager") -> None:
        self._version_manager = version_manager

    def set_summary_generator(self, summary_generator: "SummaryGenerator") -> None:
        self._summary_generator = summary_generator

    async def add_to_queue(
        self,
        item_type: str,
        data: dict[str, Any],
        document_id: str
    ) -> None:
        """Add item to pending queue."""
        item = PendingItem(item_type, data, document_id)
        await self._queue.put(item)
        logger.debug(
            "Added %s to pending queue (document: %s)",
            item_type,
            document_id
        )

    async def start(self) -> None:
        """Start the batch merger scheduler."""
        if self._running:
            logger.warning("BatchMerger already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info(
            "BatchMerger started with interval %d minutes",
            self._settings.batch_interval_minutes
        )

    async def stop(self) -> None:
        """Stop the batch merger scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("BatchMerger stopped")

    async def _run_scheduler(self) -> None:
        """Main scheduler loop."""
        interval = self._settings.batch_interval_minutes * 60  # Convert to seconds
        
        while self._running:
            try:
                await asyncio.sleep(interval)
                await self._merge_task()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in batch merger: %s", e)
                # Continue on error
                await asyncio.sleep(60)  # Wait before retry

    async def _merge_task(self) -> None:
        """Execute batch merge."""
        if not self._version_manager:
            logger.warning("Version manager not set, skipping merge")
            return
        
        # Collect pending items
        items: list[PendingItem] = []
        max_items = 100  # Process in batches
        
        while not self._queue.empty() and len(items) < max_items:
            try:
                item = self._queue.get_nowait()
                items.append(item)
            except asyncio.QueueEmpty:
                break
        
        if not items:
            logger.debug("No pending items to merge")
            return
        
        logger.info("Processing %d pending items", len(items))
        
        # Process entity versions
        entity_items = [i for i in items if i.item_type == "entity_version"]
        # Process relationship snapshots
        relationship_items = [i for i in items if i.item_type == "relationship_snapshot"]
        
        # Here we would call version_manager to persist
        # For now just log the counts
        logger.info(
            "Merging: %d entity versions, %d relationship snapshots",
            len(entity_items),
            len(relationship_items)
        )
        
        # Trigger summary generation if enabled
        if self._settings.summary_enabled and self._summary_generator:
            try:
                # Generate global summary after merge
                asyncio.create_task(
                    self._summary_generator.generate_global_summary()
                )
            except Exception as e:
                logger.warning("Failed to generate summary: %s", e)
        
        self._last_merge_time = datetime.utcnow()
        logger.info("Batch merge completed at %s", self._last_merge_time)

    def get_status(self) -> dict[str, Any]:
        """Get merger status."""
        return {
            "running": self._running,
            "pending_count": self._queue.qsize(),
            "last_merge_time": self._last_merge_time.isoformat() if self._last_merge_time else None,
            "interval_minutes": self._settings.batch_interval_minutes
        }

    async def trigger_manual_merge(self) -> dict[str, Any]:
        """Manually trigger a merge."""
        await self._merge_task()
        return self.get_status()
```

- [ ] **Step 2: 编写测试**

创建 `tests/test_temporal/test_batch_merger.py`:

```python
"""Tests for batch merger."""

import pytest
import asyncio
from datetime import datetime
from uuid import uuid4

from app.config import TemporalSettings
from app.services.temporal_knowledge.batch_merger import BatchMerger, PendingItem


@pytest.fixture
def temporal_settings():
    return TemporalSettings(batch_interval_minutes=1, summary_enabled=False)


@pytest.fixture
def batch_merger(temporal_settings):
    return BatchMerger(temporal_settings)


def test_batch_merger_initialization(batch_merger):
    assert batch_merger is not None
    assert batch_merger._running is False


def test_pending_item_creation():
    item = PendingItem(
        item_type="entity_version",
        data={"entity_id": str(uuid4())},
        document_id="doc-123"
    )
    
    assert item.item_type == "entity_version"
    assert item.data["entity_id"]
    assert item.created_at is not None


@pytest.mark.asyncio
async def test_add_to_queue(batch_merger):
    await batch_merger.add_to_queue(
        item_type="entity_version",
        data={"test": "data"},
        document_id="doc-123"
    )
    
    assert batch_merger._queue.qsize() == 1


@pytest.mark.asyncio
async def test_start_stop(batch_merger):
    await batch_merger.start()
    assert batch_merger._running is True
    
    await batch_merger.stop()
    assert batch_merger._running is False


def test_get_status(batch_merger):
    status = batch_merger.get_status()
    
    assert "running" in status
    assert "pending_count" in status
    assert "last_merge_time" in status
    assert status["interval_minutes"] == 1
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/test_temporal/test_batch_merger.py -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add app/services/temporal_knowledge/batch_merger.py tests/test_temporal/
git commit -m "feat: add batch merger"

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

---

### Task 6: 增量提取器

**Files:**
- Create: `app/services/temporal_knowledge/temporal_extractor.py`
- Test: `tests/test_temporal/test_temporal_extractor.py`

- [ ] **Step 1: 创建增量提取器**

创建 `app/services/temporal_knowledge/temporal_extractor.py`:

```python
"""Temporal extractor for incremental processing."""

import logging
from datetime import datetime
from uuid import UUID
from typing import Any

from app.domain.nodes import EntityNode, ChunkNode
from app.domain.relationships import GraphRelationship
from app.domain.temporal import EntityVersion, RelationshipSnapshot
from app.services.temporal_knowledge.version_manager import VersionManager
from app.services.temporal_knowledge.batch_merger import BatchMerger

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
            self.modified_relationships
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
    """Handles incremental extraction and version management."""

    def __init__(
        self,
        version_manager: VersionManager,
        batch_merger: BatchMerger,
        version_threshold: int = 1
    ) -> None:
        self._version_manager = version_manager
        self._batch_merger = batch_merger
        self._version_threshold = version_threshold
        self._entity_cache: dict[str, EntityNode] = {}

    def cache_entity(self, entity: EntityNode) -> None:
        """Cache entity for change detection."""
        key = f"{entity.name}|{entity.entity_type.value}"
        self._entity_cache[key] = entity

    def get_cached_entity(self, name: str, entity_type: str) -> EntityNode | None:
        """Get cached entity by name and type."""
        key = f"{name}|{entity_type}"
        return self._entity_cache.get(key)

    def detect_entity_changes(
        self,
        new_entities: list[EntityNode]
    ) -> list[EntityNode]:
        """Detect which entities are new (need version creation)."""
        new_entity_versions = []
        
        for entity in new_entities:
            key = f"{entity.name}|{entity.entity_type.value}"
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
        """Check if entity has meaningful changes."""
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
        """Detect which relationships need new snapshots."""
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
        """Process entities and create versions."""
        timestamp = timestamp or datetime.utcnow()
        
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
        """Process relationships and create snapshots."""
        timestamp = timestamp or datetime.utcnow()
        
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
        """Queue items for batch processing."""
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
```

- [ ] **Step 2: 编写测试**

创建 `tests/test_temporal/test_temporal_extractor.py`:

```python
"""Tests for temporal extractor."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from uuid import uuid4

from app.domain.enums import EntityType
from app.domain.nodes import EntityNode
from app.domain.relationships import GraphRelationship, RelationType
from app.services.temporal_knowledge.temporal_extractor import (
    TemporalExtractor,
    ChangeSet,
    VersionManager,
    BatchMerger
)
from app.config import TemporalSettings


@pytest.fixture
def version_manager():
    return MagicMock(spec=VersionManager)


@pytest.fixture
def batch_merger():
    merger = MagicMock(spec=BatchMerger)
    merger.add_to_queue = AsyncMock()
    return merger


@pytest.fixture
def temporal_settings():
    return TemporalSettings(version_threshold=1)


@pytest.fixture
def temporal_extractor(version_manager, batch_merger, temporal_settings):
    return TemporalExtractor(
        version_manager,
        batch_merger,
        temporal_settings.version_threshold
    )


def test_change_set_initialization():
    change_set = ChangeSet(
        added_entities=[],
        modified_entities=[]
    )
    assert change_set.has_changes is False
    assert change_set.change_count == 0


def test_change_set_with_changes():
    entity = EntityNode(
        id=uuid4(),
        name="Test",
        entity_type=EntityType.PERSON
    )
    
    change_set = ChangeSet(added_entities=[entity])
    assert change_set.has_changes is True
    assert change_set.change_count == 1


def test_cache_entity(temporal_extractor):
    entity = EntityNode(
        id=uuid4(),
        name="Test",
        entity_type=EntityType.PERSON
    )
    
    temporal_extractor.cache_entity(entity)
    
    cached = temporal_extractor.get_cached_entity("Test", "PERSON")
    assert cached is not None
    assert cached.name == "Test"


def test_detect_new_entity(temporal_extractor):
    entity = EntityNode(
        id=uuid4(),
        name="New Entity",
        entity_type=EntityType.PERSON,
        description="A new entity"
    )
    
    new_entities = temporal_extractor.detect_entity_changes([entity])
    
    assert len(new_entities) == 1
    assert new_entities[0].name == "New Entity"


def test_detect_modified_entity(temporal_extractor):
    old_entity = EntityNode(
        id=uuid4(),
        name="Test",
        entity_type=EntityType.PERSON,
        description="Old description"
    )
    
    new_entity = EntityNode(
        id=uuid4(),
        name="Test",
        entity_type=EntityType.PERSON,
        description="New description"
    )
    
    # Cache old entity
    temporal_extractor.cache_entity(old_entity)
    
    # Detect changes
    changed = temporal_extractor.detect_entity_changes([new_entity])
    
    assert len(changed) == 1


@pytest.mark.asyncio
async def test_process_entity_versions(temporal_extractor, version_manager):
    version_manager.create_entity_version = AsyncMock(
        return_value=MagicMock(id=uuid4())
    )
    
    entity = EntityNode(
        id=uuid4(),
        name="Test",
        entity_type=EntityType.PERSON
    )
    
    versions = await temporal_extractor.process_entity_versions([entity])
    
    assert len(versions) == 1
    version_manager.create_entity_version.assert_called_once()
```

- [ ] **Step 3: 运行测试验证**

Run: `pytest tests/test_temporal/test_temporal_extractor.py -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add app/services/temporal_knowledge/temporal_extractor.py tests/test_temporal/
git commit -m "feat: add temporal extractor"

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

---

### Task 7: 时序 API 路由

**Files:**
- Create: `app/api/routes/temporal.py`
- Modify: `app/main.py` - 注册路由和服务
- Test: `tests/test_temporal/test_temporal_api.py`

- [ ] **Step 1: 创建 API 路由**

创建 `app/api/routes/temporal.py`:

```python
"""Temporal knowledge graph API routes."""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status, Depends

from app.api.schemas.temporal import (
    TemporalQueryRequest,
    TemporalQueryResponse,
    SummaryRequest,
    SummaryResponse,
    TemporalStatusResponse,
)
from app.services.temporal_knowledge import VersionManager, SummaryGenerator, BatchMerger
from app.persistence.temporal_store import TemporalStore
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/temporal", tags=["Temporal Knowledge"])

# Global service instances (set in main.py)
_version_manager: VersionManager | None = None
_summary_generator: SummaryGenerator | None = None
_batch_merger: BatchMerger | None = None
_temporal_store: TemporalStore | None = None


def set_temporal_services(
    version_manager: VersionManager,
    summary_generator: SummaryGenerator,
    batch_merger: BatchMerger,
    temporal_store: TemporalStore
) -> None:
    """Set global temporal service instances."""
    global _version_manager, _summary_generator, _batch_merger, _temporal_store
    _version_manager = version_manager
    _summary_generator = summary_generator
    _batch_merger = batch_merger
    _temporal_store = temporal_store


def get_version_manager() -> VersionManager:
    if _version_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Temporal service not initialized"
        )
    return _version_manager


def get_summary_generator() -> SummaryGenerator:
    if _summary_generator is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Temporal service not initialized"
        )
    return _summary_generator


def get_batch_merger() -> BatchMerger:
    if _batch_merger is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Temporal service not initialized"
        )
    return _batch_merger


def get_temporal_store() -> TemporalStore:
    if _temporal_store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Temporal service not initialized"
        )
    return _temporal_store


@router.post(
    "/query",
    response_model=TemporalQueryResponse,
    summary="Query temporal data",
    description="Query entity or relationship history, or state at specific time"
)
async def query_temporal(
    request: TemporalQueryRequest,
    version_manager: VersionManager = Depends(get_version_manager)
) -> TemporalQueryResponse:
    """Query temporal data."""
    try:
        results = []
        
        if request.query_type == "history":
            if request.entity_id:
                records = await version_manager.get_entity_history(
                    request.entity_id,
                    request.from_time,
                    request.to_time
                )
                results = [
                    {
                        "entity_id": str(r.entity_id),
                        "version": r.version,
                        "timestamp": r.timestamp.isoformat(),
                        "properties": r.properties,
                        "change_summary": r.change_summary
                    }
                    for r in records
                ]
            elif request.source_id and request.target_id:
                records = await version_manager.get_relationship_history(
                    request.source_id,
                    request.target_id,
                    request.from_time,
                    request.to_time
                )
                results = [
                    {
                        "source_id": str(r.source_id),
                        "target_id": str(r.target_id),
                        "relation_type": r.relation_type,
                        "valid_from": r.valid_from.isoformat(),
                        "valid_to": r.valid_to.isoformat() if r.valid_to else None,
                        "weight": r.weight
                    }
                    for r in records
                ]
        
        elif request.query_type == "at_time":
            if request.entity_id and request.timestamp:
                record = await version_manager.get_entity_at_time(
                    request.entity_id,
                    request.timestamp
                )
                if record:
                    results = [{
                        "entity_id": str(record.entity_id),
                        "version": record.version,
                        "timestamp": record.timestamp.isoformat(),
                        "properties": record.properties
                    }]
        
        return TemporalQueryResponse(
            query_type=request.query_type,
            results=results,
            metadata={"count": len(results)}
        )
        
    except Exception as exc:
        logger.exception("Failed to query temporal data: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {exc}"
        ) from exc


@router.post(
    "/summary",
    response_model=SummaryResponse,
    summary="Generate summary",
    description="Generate entity, relationship, or global level summary"
)
async def generate_summary(
    request: SummaryRequest,
    version_manager: VersionManager = Depends(get_version_manager),
    summary_generator: SummaryGenerator = Depends(get_summary_generator),
    temporal_store: TemporalStore = Depends(get_temporal_store)
) -> SummaryResponse:
    """Generate summary at specified level."""
    try:
        if request.level == "entity":
            if not request.entity_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="entity_id required for entity-level summary"
                )
            
            # Get entity info from store
            entity_name = request.entity_name or "Unknown"
            entity_type = request.entity_type or "OTHER"
            
            summary = await summary_generator.generate_entity_summary(
                request.entity_id,
                entity_name,
                entity_type
            )
            
            content = {
                "entity_id": str(summary.entity_id),
                "entity_name": summary.entity_name,
                "entity_type": summary.entity_type,
                "current_description": summary.current_description,
                "version_count": summary.version_count,
                "change_history": [
                    {
                        "version": c["version"],
                        "timestamp": c["timestamp"],
                        "summary": c["summary"]
                    }
                    for c in summary.change_history
                ],
                "importance_score": summary.importance_score
            }
        
        elif request.level == "relationship":
            if not request.source_id or not request.target_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="source_id and target_id required for relationship-level summary"
                )
            
            summary = await summary_generator.generate_relationship_summary(
                request.source_id,
                request.target_id,
                request.source_name or "Source",
                request.target_name or "Target",
                request.relation_type or "RELATED_TO"
            )
            
            content = {
                "source_id": str(summary.source_id),
                "target_id": str(summary.target_id),
                "relation_type": summary.relation_type,
                "duration_days": summary.duration_days,
                "snapshot_count": summary.snapshot_count,
                "strength_trend": summary.strength_trend,
                "key_events": summary.key_events
            }
        
        elif request.level == "global":
            summary = await summary_generator.generate_global_summary(
                request.time_range
            )
            
            content = {
                "total_entities": summary.total_entities,
                "total_versions": summary.total_versions,
                "total_snapshots": summary.total_snapshots,
                "top_entities": summary.top_entities,
                "entity_trend": summary.entity_trend,
                "relationship_density": summary.relationship_density
            }
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid level: {request.level}"
            )
        
        return SummaryResponse(
            level=request.level,
            content=content,
            generated_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to generate summary: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Summary generation failed: {exc}"
        ) from exc


@router.get(
    "/status",
    response_model=TemporalStatusResponse,
    summary="Get temporal service status"
)
async def get_status(
    batch_merger: BatchMerger = Depends(get_batch_merger)
) -> TemporalStatusResponse:
    """Get temporal service status."""
    status = batch_merger.get_status()
    
    return TemporalStatusResponse(
        running=status["running"],
        pending_count=status["pending_count"],
        last_merge_time=datetime.fromisoformat(status["last_merge_time"]) if status["last_merge_time"] else None,
        interval_minutes=status["interval_minutes"]
    )


@router.post(
    "/merge",
    response_model=TemporalStatusResponse,
    summary="Manually trigger merge"
)
async def trigger_merge(
    batch_merger: BatchMerger = Depends(get_batch_merger)
) -> TemporalStatusResponse:
    """Manually trigger batch merge."""
    status = await batch_merger.trigger_manual_merge()
    
    return TemporalStatusResponse(
        running=status["running"],
        pending_count=status["pending_count"],
        last_merge_time=datetime.fromisoformat(status["last_merge_time"]) if status["last_merge_time"] else None,
        interval_minutes=status["interval_minutes"]
    )
```

- [ ] **Step 2: 创建 API Schema**

创建 `app/api/schemas/temporal.py`:

```python
"""Temporal API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TemporalQueryRequest(BaseModel):
    """Request for temporal queries."""
    
    entity_id: UUID | None = Field(None, description="Entity ID for entity queries")
    source_id: UUID | None = Field(None, description="Source entity ID for relationship queries")
    target_id: UUID | None = Field(None, description="Target entity ID for relationship queries")
    query_type: str = Field(..., description="history, at_time, or changes")
    from_time: datetime | None = Field(None, description="Start time for range queries")
    to_time: datetime | None = Field(None, description="End time for range queries")
    timestamp: datetime | None = Field(None, description="Specific timestamp for at_time query")


class TemporalQueryResponse(BaseModel):
    """Response for temporal queries."""
    
    query_type: str
    results: list[dict]
    metadata: dict


class SummaryRequest(BaseModel):
    """Request for summary generation."""
    
    level: str = Field(..., description="entity, relationship, or global")
    entity_id: UUID | None = Field(None, description="Entity ID for entity-level summary")
    entity_name: str | None = Field(None, description="Entity name")
    entity_type: str | None = Field(None, description="Entity type")
    source_id: UUID | None = Field(None, description="Source entity ID")
    target_id: UUID | None = Field(None, description="Target entity ID")
    source_name: str | None = Field(None, description="Source entity name")
    target_name: str | None = Field(None, description="Target entity name")
    relation_type: str | None = Field(None, description="Relation type")
    time_range: tuple[datetime, datetime] | None = Field(None, description="Time range for global summary")


class SummaryResponse(BaseModel):
    """Response for summary generation."""
    
    level: str
    content: dict
    generated_at: datetime


class TemporalStatusResponse(BaseModel):
    """Response for status queries."""
    
    running: bool
    pending_count: int
    last_merge_time: datetime | None
    interval_minutes: int
```

- [ ] **Step 3: 注册服务到 main.py**

修改 `app/main.py` 添加时序服务和路由注册:

```python
# 在 main.py 中添加导入
from app.api.routes.temporal import router as temporal_router, set_temporal_services
from app.persistence.temporal_store import TemporalStore
from app.services.temporal_knowledge import VersionManager, SummaryGenerator, BatchMerger

# 在 lifespan 函数中初始化服务
async def lifespan(app: FastAPI) -> None:
    # ... existing code ...
    
    # Initialize temporal services
    temporal_store = TemporalStore(driver)
    await temporal_store.create_indexes()
    
    version_manager = VersionManager(temporal_store)
    
    summary_generator = SummaryGenerator(
        settings.openai,
        settings.temporal
    )
    summary_generator.set_version_manager(version_manager)
    summary_generator.set_temporal_store(temporal_store)
    
    batch_merger = BatchMerger(
        settings.temporal,
        version_manager,
        summary_generator
    )
    await batch_merger.start()
    
    # Register services
    set_temporal_services(
        version_manager,
        summary_generator,
        batch_merger,
        temporal_store
    )
    
    # Register routes
    app.include_router(temporal_router)
    
    # ... rest of lifespan ...
```

- [ ] **Step 4: 编写测试**

创建 `tests/test_temporal/test_temporal_api.py`:

```python
"""Tests for temporal API."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from uuid import uuid4
from fastapi.testclient import TestClient


@pytest.fixture
def mock_services():
    version_manager = MagicMock()
    summary_generator = MagicMock()
    batch_merger = MagicMock()
    temporal_store = MagicMock()
    
    return {
        "version_manager": version_manager,
        "summary_generator": summary_generator,
        "batch_merger": batch_merger,
        "temporal_store": temporal_store
    }


def test_temporal_query_request_schema():
    from app.api.schemas.temporal import TemporalQueryRequest
    
    request = TemporalQueryRequest(
        entity_id=uuid4(),
        query_type="history"
    )
    
    assert request.entity_id is not None
    assert request.query_type == "history"


def test_summary_request_schema():
    from app.api.schemas.temporal import SummaryRequest
    
    request = SummaryRequest(
        level="entity",
        entity_id=uuid4()
    )
    
    assert request.level == "entity"
    assert request.entity_id is not None


def test_temporal_status_response_schema():
    from app.api.schemas.temporal import TemporalStatusResponse
    
    response = TemporalStatusResponse(
        running=True,
        pending_count=10,
        last_merge_time=datetime.utcnow(),
        interval_minutes=5
    )
    
    assert response.running is True
    assert response.pending_count == 10
```

- [ ] **Step 5: 运行测试验证**

Run: `pytest tests/test_temporal/test_temporal_api.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add app/api/routes/temporal.py app/api/schemas/temporal.py app/main.py tests/test_temporal/
git commit -m "feat: add temporal API routes"

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

---

## 验证方案

### 功能验证

```bash
# 1. 启动服务
uvicorn app.main:app --reload

# 2. 检查服务状态
curl http://localhost:8000/api/v1/temporal/status

# 3. 上传文档触发提取
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -F "file=@test.pdf"

# 4. 查询实体历史
curl -X POST http://localhost:8000/api/v1/temporal/query \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "实体UUID",
    "query_type": "history"
  }'

# 5. 获取实体摘要
curl -X POST http://localhost:8000/api/v1/temporal/summary \
  -H "Content-Type: application/json" \
  -d '{
    "level": "entity",
    "entity_id": "实体UUID",
    "entity_name": "实体名称",
    "entity_type": "PERSON"
  }'

# 6. 获取全局摘要
curl -X POST http://localhost:8000/api/v1/temporal/summary \
  -H "Content-Type: application/json" \
  -d '{
    "level": "global"
  }'

# 7. 手动触发合并
curl -X POST http://localhost:8000/api/v1/temporal/merge

# 8. 运行单元测试
pytest tests/test_temporal/ -v
```

### 性能基准

- 单文档处理延迟 < 5秒
- 版本查询响应 < 500ms
- 摘要生成 < 3秒