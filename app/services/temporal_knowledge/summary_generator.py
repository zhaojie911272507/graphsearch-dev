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
        self._version_manager: VersionManager | None = None  # Set via set_version_manager
        self._temporal_store: TemporalStore | None = None  # Set via set_temporal_store

    def set_version_manager(self, version_manager: VersionManager) -> None:
        self._version_manager = version_manager

    def set_temporal_store(self, temporal_store: TemporalStore) -> None:
        self._temporal_store = temporal_store

    async def generate_entity_summary(
        self,
        entity_id: UUID,
        entity_name: str,
        entity_type: str,
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
                importance_score=0.0,
            )

        # Build version history text (limit to last 10 versions)
        version_history = "\n".join(
            [
                f"v{ev.version} ({ev.timestamp.date()}): {ev.change_summary or '无变更'}"
                for ev in reversed(history[-10:])  # 只取最近10个版本
            ]
        )

        # Generate LLM summary if enabled
        current_description = history[0].properties.get("description", "")
        importance_score = min(1.0, len(history) / 10.0)  # Simple heuristic

        if self._temporal_settings.summary_enabled:
            try:
                prompt = ENTITY_SUMMARY_PROMPT.format(
                    entity_name=entity_name,
                    entity_type=entity_type,
                    version_count=len(history),
                    version_history=version_history,
                )

                response = await self._llm.ainvoke(prompt)
                content = response.content

                # Parse response
                lines = content.split("\n")
                for line in lines:
                    if line.startswith("评分:"):
                        try:
                            importance_score = float(line.split(":")[1].strip())
                        except Exception:
                            pass
            except Exception as e:
                logger.warning("Failed to parse LLM summary: %s, raw response: %s", e, content)

        # Build change history
        change_history = [
            {
                "version": ev.version,
                "timestamp": ev.timestamp.isoformat(),
                "summary": ev.change_summary,
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
            importance_score=importance_score,
        )

    async def generate_relationship_summary(
        self,
        source_id: UUID,
        target_id: UUID,
        source_name: str,
        target_name: str,
        relation_type: str,
    ) -> RelationshipSummary:
        """Generate relationship-level summary."""
        if not self._version_manager:
            raise RuntimeError("Version manager not set")

        # Get relationship history
        snapshots = await self._version_manager.get_relationship_history(source_id, target_id)

        if not snapshots:
            return RelationshipSummary(
                source_id=source_id,
                target_id=target_id,
                relation_type=relation_type,
                duration_days=0,
                snapshot_count=0,
                strength_trend="stable",
                key_events=[],
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
                "properties": s.properties,
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
            key_events=key_events,
        )

    async def generate_global_summary(
        self, time_range: tuple[datetime, datetime] | None = None
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
            relationship_density=0.0,  # TODO: Implement density calculation
        )