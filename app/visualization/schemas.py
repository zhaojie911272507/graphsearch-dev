"""Pydantic schemas for the visualization API.

Defines request/response models for graph data consumed by the frontend.
"""

from pydantic import BaseModel, Field


class GraphNodeSchema(BaseModel):
    """A node in the graph visualization.

    Compatible with D3.js force-directed layout and similar libraries.
    """

    id: str = Field(..., description="Unique node identifier (UUID string)")
    label: str = Field(..., description="Node type: Document, Chunk, Entity, Concept")
    title: str = Field(
        default="",
        description="Human-readable display text (e.g., document title, entity name)",
    )
    content_preview: str = Field(
        default="",
        max_length=200,
        description="Truncated content for tooltip or detail view",
    )


class GraphEdgeSchema(BaseModel):
    """A directed edge (relationship) between two nodes."""

    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    relation_type: str = Field(
        ...,
        description="Relationship type: HAS_CHUNK, MENTIONS, RELATED_TO, etc.",
    )
    weight: float = Field(default=1.0, ge=0.0, le=1.0)


class GraphDataResponse(BaseModel):
    """Complete graph payload for the visualization frontend."""

    nodes: list[GraphNodeSchema] = Field(default_factory=list)
    edges: list[GraphEdgeSchema] = Field(default_factory=list)


class GraphStatsResponse(BaseModel):
    """Summary statistics for the knowledge graph."""

    document_count: int = Field(default=0, ge=0)
    chunk_count: int = Field(default=0, ge=0)
    entity_count: int = Field(default=0, ge=0)
    concept_count: int = Field(default=0, ge=0)
    relationship_count: int = Field(default=0, ge=0)
