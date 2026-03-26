"""Pydantic schemas for metadata management API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class AssetListItemSchema(BaseModel):
    """A single item in the asset catalog."""

    id: UUID = Field(..., description="Unique node identifier")
    node_type: str = Field(..., description="Node type: Document, Chunk, Entity, Concept")
    name: str = Field(..., description="Display name (title, entity name, etc.)")
    entity_type: str | None = Field(default=None, description="Entity type if applicable")
    created_at: datetime = Field(..., description="Creation timestamp")
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Quality score 0-1")
    relation_count: int = Field(default=0, ge=0, description="Number of relationships")
    document_count: int = Field(default=0, ge=0, description="Number of referenced documents")
    tags: list[str] = Field(default_factory=list, description="Associated tags")
    confidence_avg: float = Field(default=0.0, ge=0.0, le=1.0, description="Average confidence")


class AssetListResponseSchema(BaseModel):
    """Paginated asset catalog response."""

    items: list[AssetListItemSchema] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    total_pages: int = Field(default=0, ge=0)


class NodeDetailSchema(BaseModel):
    """Complete node detail view."""

    id: UUID
    node_type: str
    name: str
    entity_type: str | None = None
    description: str = ""
    content_preview: str = ""
    created_at: datetime
    updated_at: datetime
    source: str
    tags: list[str] = Field(default_factory=list)
    quality_score: float = 0.0
    relation_count: int = 0
    incoming_relations: list[dict[str, Any]] = Field(default_factory=list)
    outgoing_relations: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LineagePathSchema(BaseModel):
    """A single lineage path (Document → Chunk → Entity)."""

    path: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of nodes in the path with id, type, label",
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class LineageResponseSchema(BaseModel):
    """Lineage tracing response."""

    lineage_paths: list[LineagePathSchema] = Field(default_factory=list)
    upstream_count: int = 0
    downstream_count: int = 0


class AnnotationSchema(BaseModel):
    """User annotation on a node."""

    id: UUID
    node_id: UUID
    user_id: str
    annotation_type: str  # comment, tag, correction, confidence
    content: dict[str, Any]
    status: str = "pending"  # pending, resolved, rejected
    created_at: datetime
    updated_at: datetime
    votes: list[dict[str, Any]] = Field(default_factory=list)


class AnnotationCreateSchema(BaseModel):
    """Request to create an annotation."""

    annotation_type: str = Field(..., description="comment|tag|correction|confidence")
    content: dict[str, Any] = Field(..., description="Annotation content based on type")


class AnnotationUpdateSchema(BaseModel):
    """Request to update an annotation."""

    status: str | None = None
    content: dict[str, Any] | None = None


class TagSchema(BaseModel):
    """Tag for categorization."""

    id: UUID
    name: str
    color: str = "#58a6ff"
    created_by: str
    created_at: datetime


class VoteSchema(BaseModel):
    """Vote on an annotation."""

    id: UUID
    annotation_id: UUID
    user_id: str
    vote_type: str  # APPROVE, REJECT, MODIFY
    comment: str = ""
    created_at: datetime


class VoteCreateSchema(BaseModel):
    """Request to create a vote."""

    vote_type: str
    comment: str = ""
