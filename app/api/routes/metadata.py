"""Metadata management API routes.

Provides endpoints for:
- Asset catalog browsing and search
- Node detail views
- Data lineage tracing
- Annotations and tags
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import GraphStoreDep
from app.api.schemas.metadata import (
    AnnotationCreateSchema,
    AnnotationSchema,
    AnnotationUpdateSchema,
    AssetListItemSchema,
    AssetListResponseSchema,
    LineageResponseSchema,
    NodeDetailSchema,
    TagSchema,
    VoteCreateSchema,
    VoteSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metadata", tags=["Metadata Management"])


def _calculate_quality_score(
    node_data: dict,
    relation_count: int,
    has_embedding: bool,
    confidence: float = 0.0,
) -> float:
    """Calculate quality score for a node.

    quality_score = (
        0.3 * embedding_completeness +
        0.25 * relation_density +
        0.25 * confidence_avg +
        0.2 * recency_factor
    )
    """
    embedding_score = 1.0 if has_embedding else 0.0

    relation_density = min(relation_count / 10.0, 1.0)

    recency = node_data.get("created_at", "")
    recency_score = 1.0
    if recency:
        try:
            if isinstance(recency, str):
                created = datetime.fromisoformat(recency.replace("Z", "+00:00"))
            else:
                created = recency
            days_old = (datetime.now(created.tzinfo) - created).days
            recency_score = max(0.0, min(1.0, 1.0 - (days_old / 90.0)))
        except Exception:
            pass

    score = (
        0.3 * embedding_score +
        0.25 * relation_density +
        0.25 * confidence +
        0.2 * recency_score
    )
    return round(score, 2)


@router.get(
    "/assets",
    response_model=AssetListResponseSchema,
    summary="List assets in catalog",
    description="Browse and search the asset catalog with filtering and pagination.",
)
async def list_assets(
    store: GraphStoreDep,
    type: str = Query(default="", description="Node type filter (Document, Entity, Concept, Chunk)"),
    entity_type: str = Query(default="", description="Entity type filter (PERSON, ORG, etc.)"),
    q: str = Query(default="", description="Search query"),
    tags: list[str] = Query(default=[], description="Tag filters"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at", description="Sort field"),
    order: str = Query(default="desc", description="Sort order (asc, desc)"),
) -> AssetListResponseSchema:
    """List assets from the knowledge graph with filtering and pagination."""
    try:
        assets = await store.get_metadata_assets(
            node_type=type or None,
            entity_type=entity_type or None,
            search_query=q or None,
            tags=tags or None,
            sort_by=sort_by,
            order=order,
            limit=page_size,
            offset=(page - 1) * page_size,
        )

        total = await store.count_metadata_assets(
            node_type=type or None,
            entity_type=entity_type or None,
            search_query=q or None,
            tags=tags or None,
        )

        items = []
        for asset in assets:
            has_embedding = asset.get("node_type") == "Chunk" and bool(asset.get("embedding"))
            confidence = asset.get("confidence_avg", 0.0)
            relation_count = asset.get("relation_count", 0)

            quality = _calculate_quality_score(
                asset,
                relation_count=relation_count,
                has_embedding=has_embedding,
                confidence=confidence,
            )

            items.append(AssetListItemSchema(
                id=UUID(asset["id"]),
                node_type=asset.get("node_type", "Unknown"),
                name=asset.get("name", asset.get("title", "")),
                entity_type=asset.get("entity_type"),
                created_at=datetime.fromisoformat(asset["created_at"].replace("Z", "+00:00")) if isinstance(asset["created_at"], str) else asset["created_at"],
                quality_score=quality,
                relation_count=relation_count,
                document_count=asset.get("document_count", 0),
                tags=asset.get("tags", []),
                confidence_avg=confidence,
            ))

        return AssetListResponseSchema(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size if total > 0 else 0,
        )

    except Exception as exc:
        logger.exception("Failed to list assets: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list assets: {exc}",
        ) from exc


@router.get(
    "/{node_id}",
    response_model=NodeDetailSchema,
    summary="Get node detail",
    description="Get complete details for a specific node including relations and annotations.",
)
async def get_node_detail(
    node_id: UUID,
    store: GraphStoreDep,
) -> NodeDetailSchema:
    """Get detailed information about a specific node."""
    try:
        node_data = await store.get_node_by_id(str(node_id))
        if not node_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node {node_id} not found",
            )

        relations = await store.get_node_relations(str(node_id), depth=1)

        incoming = []
        outgoing = []
        for rel in relations.get("relations", []):
            rel_info = {
                "relation_type": rel.get("relation_type", ""),
                "other_node_id": rel.get("other_node_id", ""),
                "other_node_name": rel.get("other_node_name", ""),
                "other_node_type": rel.get("other_node_type", ""),
                "weight": rel.get("weight", 1.0),
            }
            if rel.get("direction") == "incoming":
                incoming.append(rel_info)
            else:
                outgoing.append(rel_info)

        tags = node_data.get("tags", [])

        has_embedding = node_data.get("node_type") == "Chunk" and bool(node_data.get("embedding"))
        confidence = node_data.get("confidence_avg", 0.0)
        quality = _calculate_quality_score(
            node_data,
            relation_count=len(relations.get("relations", [])),
            has_embedding=has_embedding,
            confidence=confidence,
        )

        return NodeDetailSchema(
            id=UUID(node_data["id"]),
            node_type=node_data.get("node_type", "Unknown"),
            name=node_data.get("name", node_data.get("title", "")),
            entity_type=node_data.get("entity_type"),
            description=node_data.get("description", ""),
            content_preview=node_data.get("content", "")[:200] if node_data.get("content") else "",
            created_at=datetime.fromisoformat(node_data["created_at"].replace("Z", "+00:00")) if isinstance(node_data["created_at"], str) else node_data["created_at"],
            updated_at=datetime.fromisoformat(node_data["updated_at"].replace("Z", "+00:00")) if isinstance(node_data["updated_at"], str) else node_data["updated_at"],
            source=node_data.get("source", "system"),
            tags=tags,
            quality_score=quality,
            relation_count=len(relations.get("relations", [])),
            incoming_relations=incoming,
            outgoing_relations=outgoing,
            metadata={
                "content_hash": node_data.get("content_hash"),
                "chunk_index": node_data.get("chunk_index"),
                "document_id": node_data.get("document_id"),
            },
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get node detail: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get node detail: {exc}",
        ) from exc


@router.get(
    "/{node_id}/lineage",
    response_model=LineageResponseSchema,
    summary="Get data lineage",
    description="Trace the lineage of a node (upstream sources and downstream derivations).",
)
async def get_node_lineage(
    node_id: UUID,
    store: GraphStoreDep,
    direction: str = Query(default="both", description="upstream, downstream, or both"),
    max_depth: int = Query(default=3, ge=1, le=5),
) -> LineageResponseSchema:
    """Get lineage information for a node."""
    try:
        lineage_data = await store.get_node_lineage(
            str(node_id),
            direction=direction,
            max_depth=max_depth,
        )

        paths = []
        for path_data in lineage_data.get("paths", []):
            path_nodes = []
            for node in path_data.get("nodes", []):
                path_nodes.append({
                    "id": node.get("id", ""),
                    "type": node.get("node_type", node.get("type", "")),
                    "label": node.get("name", node.get("title", "")),
                })
            paths.append({
                "path": path_nodes,
                "confidence": path_data.get("confidence", 1.0),
            })

        return LineageResponseSchema(
            lineage_paths=paths,
            upstream_count=lineage_data.get("upstream_count", 0),
            downstream_count=lineage_data.get("downstream_count", 0),
        )

    except Exception as exc:
        logger.exception("Failed to get lineage: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get lineage: {exc}",
        ) from exc


@router.get(
    "/{node_id}/annotations",
    response_model=list[AnnotationSchema],
    summary="Get node annotations",
)
async def get_annotations(
    node_id: UUID,
    store: GraphStoreDep,
    annotation_type: str = Query(default="", description="Filter by type"),
    status: str = Query(default="", description="Filter by status"),
) -> list[AnnotationSchema]:
    """Get annotations for a node."""
    try:
        annotations = await store.get_node_annotations(
            str(node_id),
            annotation_type=annotation_type or None,
            status=status or None,
        )
        return [
            AnnotationSchema(
                id=UUID(a["id"]),
                node_id=UUID(a["node_id"]),
                user_id=a["user_id"],
                annotation_type=a["annotation_type"],
                content=a["content"],
                status=a["status"],
                created_at=datetime.fromisoformat(a["created_at"].replace("Z", "+00:00")) if isinstance(a["created_at"], str) else a["created_at"],
                updated_at=datetime.fromisoformat(a["updated_at"].replace("Z", "+00:00")) if isinstance(a["updated_at"], str) else a["updated_at"],
                votes=a.get("votes", []),
            )
            for a in annotations
        ]
    except Exception as exc:
        logger.exception("Failed to get annotations: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get annotations: {exc}",
        ) from exc


@router.post(
    "/{node_id}/annotations",
    response_model=AnnotationSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create annotation",
)
async def create_annotation(
    node_id: UUID,
    annotation: AnnotationCreateSchema,
    store: GraphStoreDep,
) -> AnnotationSchema:
    """Create a new annotation on a node."""
    try:
        created = await store.create_annotation(
            node_id=str(node_id),
            user_id="current_user",
            annotation_type=annotation.annotation_type,
            content=annotation.content,
        )
        return AnnotationSchema(
            id=UUID(created["id"]),
            node_id=UUID(created["node_id"]),
            user_id=created["user_id"],
            annotation_type=created["annotation_type"],
            content=created["content"],
            status=created["status"],
            created_at=datetime.fromisoformat(created["created_at"].replace("Z", "+00:00")) if isinstance(created["created_at"], str) else created["created_at"],
            updated_at=datetime.fromisoformat(created["updated_at"].replace("Z", "+00:00")) if isinstance(created["updated_at"], str) else created["updated_at"],
            votes=created.get("votes", []),
        )
    except Exception as exc:
        logger.exception("Failed to create annotation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create annotation: {exc}",
        ) from exc


@router.put(
    "/annotations/{annotation_id}",
    response_model=AnnotationSchema,
    summary="Update annotation",
)
async def update_annotation(
    annotation_id: UUID,
    annotation: AnnotationUpdateSchema,
    store: GraphStoreDep,
) -> AnnotationSchema:
    """Update an annotation."""
    try:
        update_data = {}
        if annotation.status is not None:
            update_data["status"] = annotation.status
        if annotation.content is not None:
            update_data["content"] = annotation.content

        updated = await store.update_annotation(
            str(annotation_id),
            **update_data,
        )
        return AnnotationSchema(
            id=UUID(updated["id"]),
            node_id=UUID(updated["node_id"]),
            user_id=updated["user_id"],
            annotation_type=updated["annotation_type"],
            content=updated["content"],
            status=updated["status"],
            created_at=datetime.fromisoformat(updated["created_at"].replace("Z", "+00:00")) if isinstance(updated["created_at"], str) else updated["created_at"],
            updated_at=datetime.fromisoformat(updated["updated_at"].replace("Z", "+00:00")) if isinstance(updated["updated_at"], str) else updated["updated_at"],
            votes=updated.get("votes", []),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update annotation: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update annotation: {exc}",
        ) from exc


@router.post(
    "/annotations/{annotation_id}/votes",
    response_model=VoteSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Vote on annotation",
)
async def vote_annotation(
    annotation_id: UUID,
    vote: VoteCreateSchema,
    store: GraphStoreDep,
) -> VoteSchema:
    """Cast a vote on an annotation."""
    try:
        created = await store.create_vote(
            annotation_id=str(annotation_id),
            user_id="current_user",
            vote_type=vote.vote_type,
            comment=vote.comment,
        )
        return VoteSchema(
            id=UUID(created["id"]),
            annotation_id=UUID(created["annotation_id"]),
            user_id=created["user_id"],
            vote_type=created["vote_type"],
            comment=created.get("comment", ""),
            created_at=datetime.fromisoformat(created["created_at"].replace("Z", "+00:00")) if isinstance(created["created_at"], str) else created["created_at"],
        )
    except Exception as exc:
        logger.exception("Failed to create vote: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create vote: {exc}",
        ) from exc


@router.get(
    "/{node_id}/tags",
    response_model=list[TagSchema],
    summary="Get node tags",
)
async def get_tags(
    node_id: UUID,
    store: GraphStoreDep,
) -> list[TagSchema]:
    """Get tags for a node."""
    try:
        tags = await store.get_node_tags(str(node_id))
        return [
            TagSchema(
                id=UUID(t["id"]),
                name=t["name"],
                color=t.get("color", "#58a6ff"),
                created_by=t["created_by"],
                created_at=datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")) if isinstance(t["created_at"], str) else t["created_at"],
            )
            for t in tags
        ]
    except Exception as exc:
        logger.exception("Failed to get tags: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tags: {exc}",
        ) from exc
