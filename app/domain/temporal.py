"""Temporal knowledge graph domain models.

This module provides models for tracking entity and relationship versions over time,
enabling temporal queries and historical analysis of the knowledge graph.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import NodeType


class EntityVersion(BaseModel):
    """实体版本快照 - 存储实体在特定时间点的状态

    EntityVersion tracks the state of an entity at a specific point in time,
    enabling historical queries and change tracking.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4, description="Unique version identifier")
    entity_id: UUID = Field(..., description="关联的主实体 ID")
    version: int = Field(..., ge=1, description="版本号递增")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="版本创建时间")
    properties: dict[str, Any] = Field(default_factory=dict, description="快照时的完整属性")
    change_summary: str = Field(default="", description="变更摘要")
    source_document_ids: list[str] = Field(default_factory=list, description="关联的文档 ID 列表")

    def neo4j_properties(self) -> dict[str, object]:
        """Serialize to a flat dict suitable for Neo4j parameter injection."""
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
    """关系快照 - 记录关系在特定时间区间的状态

    RelationshipSnapshot tracks the state of a relationship over time,
    with valid_from and valid_to timestamps to represent temporal validity.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4, description="Unique snapshot identifier")
    source_id: UUID = Field(..., description="源实体 ID")
    target_id: UUID = Field(..., description="目标实体 ID")
    relation_type: str = Field(..., description="关系类型")
    valid_from: datetime = Field(default_factory=datetime.utcnow, description="生效起始时间")
    valid_to: datetime | None = Field(default=None, description="生效结束时间，None 表示当前有效")
    properties: dict[str, Any] = Field(default_factory=dict, description="关系属性")
    weight: float = Field(default=0.5, ge=0.0, le=1.0, description="关系权重")
    is_current: bool = Field(default=True, description="是否为当前活跃关系")

    def neo4j_properties(self) -> dict[str, object]:
        """Serialize to a flat dict suitable for Neo4j parameter injection."""
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
    """实体级摘要 - 汇总实体的版本历史和统计信息"""

    entity_id: UUID = Field(..., description="实体 ID")
    entity_name: str = Field(..., description="实体名称")
    entity_type: str = Field(..., description="实体类型")
    current_description: str = Field(default="", description="当前描述")
    version_count: int = Field(default=0, ge=0, description="版本总数")
    first_seen: datetime = Field(..., description="首次出现时间")
    last_updated: datetime = Field(..., description="最后更新时间")
    change_history: list[dict[str, Any]] = Field(default_factory=list, description="变更历史")
    importance_score: float = Field(default=0.0, ge=0.0, le=1.0, description="重要性评分")


class RelationshipSummary(BaseModel):
    """关系级摘要 - 汇总关系的快照历史和统计信息"""

    source_id: UUID = Field(..., description="源实体 ID")
    target_id: UUID = Field(..., description="目标实体 ID")
    relation_type: str = Field(..., description="关系类型")
    duration_days: int = Field(default=0, ge=0, description="关系持续天数")
    snapshot_count: int = Field(default=0, ge=0, description="快照总数")
    strength_trend: str = Field(default="stable", description="强度趋势: rising/declining/stable")
    key_events: list[dict[str, Any]] = Field(default_factory=list, description="关键事件列表")


class GlobalSummary(BaseModel):
    """全局级摘要 - 整个图的时序统计信息"""

    generated_at: datetime = Field(default_factory=datetime.utcnow, description="生成时间")
    total_entities: int = Field(default=0, ge=0, description="实体总数")
    total_versions: int = Field(default=0, ge=0, description="版本总数")
    total_snapshots: int = Field(default=0, ge=0, description="关系快照总数")
    top_entities: list[dict[str, Any]] = Field(default_factory=list, description="最重要的实体列表")
    entity_trend: dict[str, Any] = Field(default_factory=dict, description="实体趋势统计")
    relationship_density: float = Field(default=0.0, ge=0.0, description="关系密度")


# Type alias for temporal node handling
TemporalNode = EntityVersion | RelationshipSnapshot