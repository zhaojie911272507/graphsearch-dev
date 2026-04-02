"""Temporal API routes.

Provides endpoints for:
- Temporal queries (time travel queries)
- Summary generation (entity, relationship, global)
- Status monitoring
- Manual merge trigger
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.schemas.temporal import (
    TemporalQueryRequest,
    TemporalQueryResponse,
    SummaryRequest,
    SummaryResponse,
    TemporalStatusResponse,
    MergeResponse,
)

logger = logging.getLogger(__name__)

# Global service instances (set via set_temporal_services)
_temporal_store = None
_version_manager = None
_summary_generator = None
_batch_merger = None


def set_temporal_services(
    temporal_store,
    version_manager,
    summary_generator,
    batch_merger,
) -> None:
    """Set global temporal service instances."""
    global _temporal_store, _version_manager, _summary_generator, _batch_merger
    _temporal_store = temporal_store
    _version_manager = version_manager
    _summary_generator = summary_generator
    _batch_merger = batch_merger


router = APIRouter(prefix="/temporal", tags=["Temporal Knowledge Graph"])


@router.post(
    "/query",
    response_model=TemporalQueryResponse,
    summary="Temporal query",
    description="Query entity or relationship at a specific time or time range.",
)
async def temporal_query(request: TemporalQueryRequest) -> TemporalQueryResponse:
    """Execute temporal query."""
    if not _version_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Temporal services not initialized",
        )

    try:
        results = []
        metadata = {}

        if request.query_type == "entity_history":
            if not request.entity_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="entity_id required for entity_history query",
                )

            history = await _version_manager.get_entity_history(
                request.entity_id,
                request.from_time,
                request.to_time,
            )
            results = [
                {
                    "id": str(h.id),
                    "entity_id": str(h.entity_id),
                    "version": h.version,
                    "timestamp": h.timestamp.isoformat(),
                    "properties": h.properties,
                    "change_summary": h.change_summary,
                }
                for h in history
            ]
            metadata = {"count": len(results)}

        elif request.query_type == "entity_at_time":
            if not request.entity_id or not request.timestamp:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="entity_id and timestamp required for entity_at_time query",
                )

            version = await _version_manager.get_entity_at_time(
                request.entity_id,
                request.timestamp,
            )
            if version:
                results = [
                    {
                        "id": str(version.id),
                        "entity_id": str(version.entity_id),
                        "version": version.version,
                        "timestamp": version.timestamp.isoformat(),
                        "properties": version.properties,
                        "change_summary": version.change_summary,
                    }
                ]
            metadata = {"count": len(results)}

        elif request.query_type == "relationship_history":
            if not request.source_id or not request.target_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="source_id and target_id required for relationship_history query",
                )

            history = await _version_manager.get_relationship_history(
                request.source_id,
                request.target_id,
                request.from_time,
                request.to_time,
            )
            results = [
                {
                    "id": str(h.id),
                    "source_id": str(h.source_id),
                    "target_id": str(h.target_id),
                    "relation_type": h.relation_type,
                    "valid_from": h.valid_from.isoformat(),
                    "valid_to": h.valid_to.isoformat() if h.valid_to else None,
                    "weight": h.weight,
                    "properties": h.properties,
                    "is_current": h.is_current,
                }
                for h in history
            ]
            metadata = {"count": len(results)}

        elif request.query_type == "current_relationship":
            if not request.source_id or not request.target_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="source_id and target_id required for current_relationship query",
                )

            rel = await _version_manager.get_current_relationship(
                request.source_id,
                request.target_id,
            )
            if rel:
                results = [
                    {
                        "id": str(rel.id),
                        "source_id": str(rel.source_id),
                        "target_id": str(rel.target_id),
                        "relation_type": rel.relation_type,
                        "valid_from": rel.valid_from.isoformat(),
                        "valid_to": rel.valid_to.isoformat() if rel.valid_to else None,
                        "weight": rel.weight,
                        "properties": rel.properties,
                        "is_current": rel.is_current,
                    }
                ]
            metadata = {"count": len(results)}

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown query_type: {request.query_type}",
            )

        return TemporalQueryResponse(
            query_type=request.query_type,
            results=results,
            metadata=metadata,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to execute temporal query: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute temporal query: {exc}",
        ) from exc


@router.post(
    "/summary",
    response_model=SummaryResponse,
    summary="Generate summary",
    description="Generate entity-level, relationship-level, or global-level summary.",
)
async def generate_summary(request: SummaryRequest) -> SummaryResponse:
    """Generate summary at specified level."""
    if not _summary_generator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Temporal services not initialized",
        )

    try:
        content = {}

        if request.level == "entity":
            if not request.entity_id or not request.entity_name or not request.entity_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="entity_id, entity_name, and entity_type required for entity summary",
                )

            summary = await _summary_generator.generate_entity_summary(
                request.entity_id,
                request.entity_name,
                request.entity_type,
            )
            content = {
                "entity_id": str(summary.entity_id),
                "entity_name": summary.entity_name,
                "entity_type": summary.entity_type,
                "current_description": summary.current_description,
                "version_count": summary.version_count,
                "first_seen": summary.first_seen.isoformat(),
                "last_updated": summary.last_updated.isoformat(),
                "change_history": summary.change_history,
                "importance_score": summary.importance_score,
            }

        elif request.level == "relationship":
            if not all([request.source_id, request.target_id, request.relation_type]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="source_id, target_id, and relation_type required for relationship summary",
                )

            summary = await _summary_generator.generate_relationship_summary(
                request.source_id,
                request.target_id,
                request.source_name or "Unknown",
                request.target_name or "Unknown",
                request.relation_type,
            )
            content = {
                "source_id": str(summary.source_id),
                "target_id": str(summary.target_id),
                "relation_type": summary.relation_type,
                "duration_days": summary.duration_days,
                "snapshot_count": summary.snapshot_count,
                "strength_trend": summary.strength_trend,
                "key_events": summary.key_events,
            }

        elif request.level == "global":
            summary = await _summary_generator.generate_global_summary(request.time_range)
            content = {
                "total_entities": summary.total_entities,
                "total_versions": summary.total_versions,
                "total_snapshots": summary.total_snapshots,
                "top_entities": summary.top_entities,
                "entity_trend": summary.entity_trend,
                "relationship_density": summary.relationship_density,
            }

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid level: {request.level}. Must be 'entity', 'relationship', or 'global'",
            )

        return SummaryResponse(
            level=request.level,
            content=content,
            generated_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to generate summary: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate summary: {exc}",
        ) from exc


@router.get(
    "/status",
    response_model=TemporalStatusResponse,
    summary="Get temporal service status",
    description="Get the current status of temporal services including batch merger.",
)
async def get_status() -> TemporalStatusResponse:
    """Get temporal services status."""
    if not _batch_merger:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Temporal services not initialized",
        )

    try:
        status_info = _batch_merger.get_status()

        return TemporalStatusResponse(
            running=status_info["running"],
            pending_count=status_info["pending_count"],
            last_merge_time=datetime.fromisoformat(status_info["last_merge_time"]) if status_info["last_merge_time"] else None,
            interval_minutes=status_info["interval_minutes"],
        )

    except Exception as exc:
        logger.exception("Failed to get status: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {exc}",
        ) from exc


@router.post(
    "/merge",
    response_model=MergeResponse,
    summary="Trigger manual merge",
    description="Manually trigger a batch merge operation.",
)
async def trigger_merge() -> MergeResponse:
    """Manually trigger batch merge."""
    if not _batch_merger:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Temporal services not initialized",
        )

    try:
        status_info = await _batch_merger.trigger_manual_merge()

        return MergeResponse(
            success=True,
            status=TemporalStatusResponse(
                running=status_info["running"],
                pending_count=status_info["pending_count"],
                last_merge_time=datetime.fromisoformat(status_info["last_merge_time"]) if status_info["last_merge_time"] else None,
                interval_minutes=status_info["interval_minutes"],
            ),
        )

    except Exception as exc:
        logger.exception("Failed to trigger merge: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger merge: {exc}",
        ) from exc