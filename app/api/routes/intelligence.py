"""Collective intelligence API routes.

Provides endpoints for:
- Review queue management
- Voting on extractions
- Exploration path saving and sharing
- Recommendations
"""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import GraphStoreDep
from app.api.schemas.intelligence import (
    AnnotationSummarySchema,
    ExplorationPathCreateSchema,
    ExplorationPathSchema,
    ExplorationPathUpdateSchema,
    RecommendationSchema,
    ReviewQueueItemSchema,
    ShareExplorationResponseSchema,
    UserContributionSchema,
    VoteCreateSchema,
    VoteResultSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/intelligence", tags=["Collective Intelligence"])


@router.get(
    "/review-queue",
    response_model=list[ReviewQueueItemSchema],
    summary="Get review queue",
    description="Get items pending review in the collaborative审核 queue.",
)
async def get_review_queue(
    store: GraphStoreDep,
    status_filter: str = Query(default="pending", description="pending, reviewed, escalated"),
    my_turn: bool = Query(default=False, description="Only items needing my review"),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[ReviewQueueItemSchema]:
    """Get review queue items."""
    try:
        items = await store.get_review_queue_items(
            status=status_filter,
            limit=limit,
        )

        result = []
        for item in items:
            result.append(ReviewQueueItemSchema(
                id=UUID(item["id"]),
                node_id=UUID(item["node_id"]),
                node_type=item.get("node_type", "Entity"),
                node_name=item.get("node_name", ""),
                reason=item.get("reason", ""),
                auto_confidence=item.get("auto_confidence", 0.0),
                source_document=item.get("source_document", ""),
                original_text=item.get("original_text", ""),
                status=item.get("status", "PENDING"),
                vote_count=item.get("vote_count", 0),
                approve_count=item.get("approve_count", 0),
                reject_count=item.get("reject_count", 0),
                modify_count=item.get("modify_count", 0),
                created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")) if isinstance(item["created_at"], str) else item["created_at"],
                priority=item.get("priority", 0.0),
            ))

        return result
    except Exception as exc:
        logger.exception("Failed to get review queue: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get review queue: {exc}",
        ) from exc


@router.post(
    "/review-queue/{item_id}/vote",
    response_model=VoteResultSchema,
    summary="Vote on review item",
)
async def vote_review_item(
    item_id: UUID,
    vote: VoteCreateSchema,
    store: GraphStoreDep,
) -> VoteResultSchema:
    """Cast a vote on a review queue item."""
    try:
        result = await store.create_review_vote(
            item_id=str(item_id),
            user_id="current_user",
            vote_type=vote.vote_type,
            comment=vote.comment,
            suggested_changes=vote.suggested_changes,
        )

        is_decisive = result.get("is_decisive", False)

        return VoteResultSchema(
            vote_id=UUID(result["id"]),
            item_id=UUID(result["item_id"]),
            user_id=result["user_id"],
            vote_type=result["vote_type"],
            comment=result.get("comment", ""),
            created_at=datetime.fromisoformat(result["created_at"].replace("Z", "+00:00")) if isinstance(result["created_at"], str) else datetime.utcnow(),
            is_decisive=is_decisive,
        )
    except Exception as exc:
        logger.exception("Failed to vote on review item: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to vote on review item: {exc}",
        ) from exc


@router.get(
    "/explorations",
    response_model=list[ExplorationPathSchema],
    summary="List exploration paths",
)
async def list_explorations(
    store: GraphStoreDep,
    user_id: str | None = Query(default=None, description="Filter by user"),
    sort: str = Query(default="created_at", description="created_at, view_count, likes"),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[ExplorationPathSchema]:
    """List exploration paths."""
    try:
        paths = await store.get_exploration_paths(
            user_id=user_id,
            sort_by=sort,
            limit=limit,
        )

        return [
            ExplorationPathSchema(
                id=UUID(p["id"]),
                user_id=p["user_id"],
                title=p["title"],
                description=p.get("description", ""),
                start_node_id=UUID(p["start_node_id"]),
                visited_nodes=[UUID(n) for n in p.get("visited_nodes", [])],
                highlights=[UUID(h) for h in p.get("highlights", [])],
                view_count=p.get("view_count", 0),
                likes=p.get("likes", 0),
                is_public=p.get("is_public", False),
                created_at=datetime.fromisoformat(p["created_at"].replace("Z", "+00:00")) if isinstance(p["created_at"], str) else p["created_at"],
                updated_at=datetime.fromisoformat(p["updated_at"].replace("Z", "+00:00")) if isinstance(p["updated_at"], str) else p["updated_at"],
            )
            for p in paths
        ]
    except Exception as exc:
        logger.exception("Failed to list explorations: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list explorations: {exc}",
        ) from exc


@router.get(
    "/explorations/{exploration_id}",
    response_model=ExplorationPathSchema,
    summary="Get exploration path",
)
async def get_exploration(
    exploration_id: UUID,
    store: GraphStoreDep,
) -> ExplorationPathSchema:
    """Get details of an exploration path."""
    try:
        path = await store.get_exploration_by_id(str(exploration_id))
        if not path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Exploration {exploration_id} not found",
            )

        await store.increment_exploration_views(str(exploration_id))

        return ExplorationPathSchema(
            id=UUID(path["id"]),
            user_id=path["user_id"],
            title=path["title"],
            description=path.get("description", ""),
            start_node_id=UUID(path["start_node_id"]),
            visited_nodes=[UUID(n) for n in path.get("visited_nodes", [])],
            highlights=[UUID(h) for h in path.get("highlights", [])],
            view_count=path.get("view_count", 0) + 1,
            likes=path.get("likes", 0),
            is_public=path.get("is_public", False),
            created_at=datetime.fromisoformat(path["created_at"].replace("Z", "+00:00")) if isinstance(path["created_at"], str) else path["created_at"],
            updated_at=datetime.fromisoformat(path["updated_at"].replace("Z", "+00:00")) if isinstance(path["updated_at"], str) else path["updated_at"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get exploration: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get exploration: {exc}",
        ) from exc


@router.post(
    "/explorations",
    response_model=ExplorationPathSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Save exploration path",
)
async def create_exploration(
    exploration: ExplorationPathCreateSchema,
    store: GraphStoreDep,
) -> ExplorationPathSchema:
    """Save a new exploration path."""
    try:
        created = await store.create_exploration_path(
            user_id="current_user",
            title=exploration.title,
            description=exploration.description,
            start_node_id=str(exploration.start_node_id),
            visited_nodes=[str(n) for n in exploration.visited_nodes],
            highlights=[str(h) for h in exploration.highlights],
            is_public=exploration.is_public,
        )

        return ExplorationPathSchema(
            id=UUID(created["id"]),
            user_id=created["user_id"],
            title=created["title"],
            description=created.get("description", ""),
            start_node_id=UUID(created["start_node_id"]),
            visited_nodes=[UUID(n) for n in created.get("visited_nodes", [])],
            highlights=[UUID(h) for h in created.get("highlights", [])],
            view_count=0,
            likes=0,
            is_public=created.get("is_public", False),
            created_at=datetime.fromisoformat(created["created_at"].replace("Z", "+00:00")) if isinstance(created["created_at"], str) else datetime.utcnow(),
            updated_at=datetime.fromisoformat(created["updated_at"].replace("Z", "+00:00")) if isinstance(created["updated_at"], str) else datetime.utcnow(),
        )
    except Exception as exc:
        logger.exception("Failed to create exploration: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create exploration: {exc}",
        ) from exc


@router.put(
    "/explorations/{exploration_id}",
    response_model=ExplorationPathSchema,
    summary="Update exploration path",
)
async def update_exploration(
    exploration_id: UUID,
    exploration: ExplorationPathUpdateSchema,
    store: GraphStoreDep,
) -> ExplorationPathSchema:
    """Update an exploration path."""
    try:
        update_data = {}
        if exploration.title is not None:
            update_data["title"] = exploration.title
        if exploration.description is not None:
            update_data["description"] = exploration.description
        if exploration.highlights is not None:
            update_data["highlights"] = [str(h) for h in exploration.highlights]
        if exploration.is_public is not None:
            update_data["is_public"] = exploration.is_public

        updated = await store.update_exploration_path(
            str(exploration_id),
            **update_data,
        )

        return ExplorationPathSchema(
            id=UUID(updated["id"]),
            user_id=updated["user_id"],
            title=updated["title"],
            description=updated.get("description", ""),
            start_node_id=UUID(updated["start_node_id"]),
            visited_nodes=[UUID(n) for n in updated.get("visited_nodes", [])],
            highlights=[UUID(h) for h in updated.get("highlights", [])],
            view_count=updated.get("view_count", 0),
            likes=updated.get("likes", 0),
            is_public=updated.get("is_public", False),
            created_at=datetime.fromisoformat(updated["created_at"].replace("Z", "+00:00")) if isinstance(updated["created_at"], str) else updated["created_at"],
            updated_at=datetime.fromisoformat(updated["updated_at"].replace("Z", "+00:00")) if isinstance(updated["updated_at"], str) else updated["updated_at"],
        )
    except Exception as exc:
        logger.exception("Failed to update exploration: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update exploration: {exc}",
        ) from exc


@router.delete(
    "/explorations/{exploration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete exploration path",
)
async def delete_exploration(
    exploration_id: UUID,
    store: GraphStoreDep,
) -> None:
    """Delete an exploration path."""
    try:
        await store.delete_exploration_path(str(exploration_id))
    except Exception as exc:
        logger.exception("Failed to delete exploration: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete exploration: {exc}",
        ) from exc


@router.post(
    "/explorations/{exploration_id}/share",
    response_model=ShareExplorationResponseSchema,
    summary="Share exploration",
)
async def share_exploration(
    exploration_id: UUID,
    store: GraphStoreDep,
    expires_in_days: int = Query(default=7, ge=1, le=30),
) -> ShareExplorationResponseSchema:
    """Generate a shareable link for an exploration."""
    try:
        import secrets

        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        await store.create_exploration_share_token(
            str(exploration_id),
            token=token,
            expires_at=expires_at,
        )

        return ShareExplorationResponseSchema(
            share_id=exploration_id,
            share_url=f"/explore/{token}",
            token=token,
            expires_at=expires_at,
        )
    except Exception as exc:
        logger.exception("Failed to share exploration: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to share exploration: {exc}",
        ) from exc


@router.post(
    "/explorations/{exploration_id}/like",
    summary="Like an exploration",
)
async def like_exploration(
    exploration_id: UUID,
    store: GraphStoreDep,
) -> dict:
    """Like an exploration path."""
    try:
        new_count = await store.increment_exploration_likes(str(exploration_id))
        return {
            "success": True,
            "likes": new_count,
        }
    except Exception as exc:
        logger.exception("Failed to like exploration: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to like exploration: {exc}",
        ) from exc


@router.get(
    "/recommendations",
    response_model=list[RecommendationSchema],
    summary="Get recommendations",
    description="Get AI-recommended related nodes based on graph structure.",
)
async def get_recommendations(
    store: GraphStoreDep,
    node_id: UUID | None = Query(default=None, description="Get recommendations for this node"),
    recommendation_type: str | None = Query(default=None, description="Filter by type"),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[RecommendationSchema]:
    """Get node recommendations based on graph structure."""
    try:
        recs = await store.get_recommendations(
            node_id=str(node_id) if node_id else None,
            recommendation_type=recommendation_type,
            limit=limit,
        )

        return [
            RecommendationSchema(
                id=UUID(r["id"]) if r.get("id") else None,
                recommendation_type=r["recommendation_type"],
                source_node_id=UUID(r["source_node_id"]),
                target_node_id=UUID(r["target_node_id"]) if r.get("target_node_id") else None,
                target_node_name=r["target_node_name"],
                target_node_type=r["target_node_type"],
                confidence=r.get("confidence", 0.0),
                reason=r["reason"],
                metadata=r.get("metadata", {}),
            )
            for r in recs
        ]
    except Exception as exc:
        logger.exception("Failed to get recommendations: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendations: {exc}",
        ) from exc


@router.get(
    "/annotations/summary/{node_id}",
    response_model=AnnotationSummarySchema,
    summary="Get annotation summary",
)
async def get_annotation_summary(
    node_id: UUID,
    store: GraphStoreDep,
) -> AnnotationSummarySchema:
    """Get summary of annotations on a node."""
    try:
        summary = await store.get_annotation_summary(str(node_id))

        return AnnotationSummarySchema(
            total_count=summary.get("total_count", 0),
            comment_count=summary.get("comment_count", 0),
            tag_count=summary.get("tag_count", 0),
            correction_count=summary.get("correction_count", 0),
            confidence_count=summary.get("confidence_count", 0),
            avg_confidence_score=summary.get("avg_confidence_score", 0.0),
            pending_corrections=summary.get("pending_corrections", 0),
            resolved_count=summary.get("resolved_count", 0),
        )
    except Exception as exc:
        logger.exception("Failed to get annotation summary: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get annotation summary: {exc}",
        ) from exc


@router.get(
    "/users/{user_id}/contributions",
    response_model=UserContributionSchema,
    summary="Get user contributions",
)
async def get_user_contributions(
    user_id: str,
    store: GraphStoreDep,
) -> UserContributionSchema:
    """Get contribution statistics for a user."""
    try:
        contributions = await store.get_user_contributions(user_id)

        return UserContributionSchema(
            user_id=contributions.get("user_id", user_id),
            username=contributions.get("username", user_id),
            annotations_count=contributions.get("annotations_count", 0),
            votes_count=contributions.get("votes_count", 0),
            explorations_count=contributions.get("explorations_count", 0),
            accepted_corrections=contributions.get("accepted_corrections", 0),
            reputation_score=contributions.get("reputation_score", 0.0),
        )
    except Exception as exc:
        logger.exception("Failed to get user contributions: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user contributions: {exc}",
        ) from exc
