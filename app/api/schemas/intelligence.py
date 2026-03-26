"""Pydantic schemas for collective intelligence API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewQueueItemSchema(BaseModel):
    """Item in the review queue."""

    id: UUID
    node_id: UUID
    node_type: str
    node_name: str
    reason: str = Field(..., description="Why this item needs review")
    auto_confidence: float = Field(..., ge=0.0, le=1.0)
    source_document: str = Field(default="", description="Source document title")
    original_text: str = Field(default="", description="Original text chunk")
    status: str = Field(..., description="PENDING, REVIEWED, ESCALATED")
    vote_count: int = Field(default=0)
    approve_count: int = Field(default=0)
    reject_count: int = Field(default=0)
    modify_count: int = Field(default=0)
    created_at: datetime
    priority: float = Field(default=0.0, description="Priority score for sorting")


class VoteCreateSchema(BaseModel):
    """Request to cast a vote on a review item."""

    vote_type: str = Field(..., description="APPROVE, REJECT, or MODIFY")
    comment: str = Field(default="", max_length=500)
    suggested_changes: dict | None = Field(default=None, description="If MODIFY, what to change")


class VoteResultSchema(BaseModel):
    """Result of a vote."""

    vote_id: UUID
    item_id: UUID
    user_id: str
    vote_type: str
    created_at: datetime
    is_decisive: bool = Field(default=False, description="Whether this vote was the deciding one")


class ExplorationPathSchema(BaseModel):
    """Saved exploration path."""

    id: UUID
    user_id: str
    title: str = Field(..., max_length=200)
    description: str = Field(default="", max_length=1000)
    start_node_id: UUID
    visited_nodes: list[UUID] = Field(default_factory=list, description="Node IDs in visit order")
    highlights: list[UUID] = Field(default_factory=list, description="Highlighted node IDs")
    view_count: int = Field(default=0)
    likes: int = Field(default=0)
    is_public: bool = Field(default=False)
    created_at: datetime
    updated_at: datetime


class ExplorationPathCreateSchema(BaseModel):
    """Request to save an exploration path."""

    title: str = Field(..., max_length=200)
    description: str = Field(default="", max_length=1000)
    start_node_id: UUID
    visited_nodes: list[UUID] = Field(default_factory=list)
    highlights: list[UUID] = Field(default_factory=list)
    is_public: bool = Field(default=False)


class ExplorationPathUpdateSchema(BaseModel):
    """Request to update an exploration path."""

    title: str | None = None
    description: str | None = None
    highlights: list[UUID] | None = None
    is_public: bool | None = None


class ShareExplorationResponseSchema(BaseModel):
    """Response for sharing an exploration."""

    share_id: UUID
    share_url: str
    token: str
    expires_at: datetime | None = None


class RecommendationSchema(BaseModel):
    """Recommended node or relationship."""

    id: UUID | None = None
    recommendation_type: str = Field(..., description="RELATED_ENTITY, SIMILAR_NODE, MISSING_RELATION")
    source_node_id: UUID
    target_node_id: UUID | None = None
    target_node_name: str = Field(..., description="Name of recommended node")
    target_node_type: str = Field(..., description="Type of recommended node")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Recommendation confidence")
    reason: str = Field(..., description="Why this is recommended")
    metadata: dict = Field(default_factory=dict)


class AnnotationSummarySchema(BaseModel):
    """Summary of annotations on a node."""

    total_count: int = 0
    comment_count: int = 0
    tag_count: int = 0
    correction_count: int = 0
    confidence_count: int = 0
    avg_confidence_score: float = 0.0
    pending_corrections: int = 0
    resolved_count: int = 0


class UserContributionSchema(BaseModel):
    """User contribution statistics."""

    user_id: str
    username: str
    annotations_count: int = 0
    votes_count: int = 0
    explorations_count: int = 0
    accepted_corrections: int = 0
    reputation_score: float = 0.0
