"""Pydantic schemas for ontology management API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EntityTypeSchema(BaseModel):
    """Entity type definition."""

    name: str = Field(..., description="Type name (e.g., PERSON, ORGANIZATION)")
    description: str = Field(default="", description="Type description")
    color: str = Field(default="#58a6ff", description="Display color for UI")
    icon: str = Field(default="circle", description="Icon name for UI")
    is_builtin: bool = Field(default=False, description="Whether this is a built-in type")
    instance_count: int = Field(default=0, description="Number of instances in graph")
    extraction_prompt_template: str = Field(default="", description="Prompt template for extraction")
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)


class EntityTypeCreateSchema(BaseModel):
    """Request to create an entity type."""

    name: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Z_]+$")
    description: str = Field(default="", max_length=500)
    color: str = Field(default="#58a6ff")
    icon: str = Field(default="circle")
    extraction_prompt_template: str = Field(default="")


class EntityTypeUpdateSchema(BaseModel):
    """Request to update an entity type."""

    description: str | None = None
    color: str | None = None
    icon: str | None = None
    extraction_prompt_template: str | None = None


class RelationTypeSchema(BaseModel):
    """Relation type definition."""

    name: str = Field(..., description="Relation name (e.g., WORKS_FOR, LOCATED_IN)")
    description: str = Field(default="", description="Relation description")
    source_types: list[str] = Field(default_factory=list, description="Allowed source entity types")
    target_types: list[str] = Field(default_factory=list, description="Allowed target entity types")
    directionality: str = Field(default="DIRECTED", description="DIRECTED or UNDIRECTED")
    is_builtin: bool = Field(default=False, description="Whether this is a built-in relation")
    instance_count: int = Field(default=0, description="Number of relationships in graph")
    properties: list[dict[str, str]] = Field(default_factory=list, description="Relation properties")
    extraction_prompt: str = Field(default="", description="Prompt template for extraction")


class RelationTypeCreateSchema(BaseModel):
    """Request to create a relation type."""

    name: str = Field(..., min_length=1, max_length=50, pattern=r"^[A-Z_]+$")
    description: str = Field(default="", max_length=500)
    source_types: list[str] = Field(default_factory=list)
    target_types: list[str] = Field(default_factory=list)
    directionality: str = Field(default="DIRECTED")
    properties: list[dict[str, str]] = Field(default_factory=list)
    extraction_prompt: str = Field(default="")


class RelationTypeUpdateSchema(BaseModel):
    """Request to update a relation type."""

    description: str | None = None
    source_types: list[str] | None = None
    target_types: list[str] | None = None
    directionality: str | None = None
    properties: list[dict[str, str]] | None = None
    extraction_prompt: str | None = None


class OntologyVersionSchema(BaseModel):
    """Ontology version record."""

    version: str = Field(..., description="Version string (e.g., v1.0.0)")
    created_at: datetime = Field(..., description="Creation timestamp")
    created_by: str = Field(..., description="User who created this version")
    change_summary: str = Field(default="", description="Summary of changes")
    changes: list[str] = Field(default_factory=list, description="List of specific changes")
    is_active: bool = Field(default=False, description="Whether this is the active version")


class OntologyVersionCreateSchema(BaseModel):
    """Request to create a new ontology version."""

    version: str = Field(..., pattern=r"^v\d+\.\d+\.\d+$")
    change_summary: str = Field(..., max_length=500)
    changes: list[str] = Field(default_factory=list)


class OntologyDiffSchema(BaseModel):
    """Diff between two ontology versions."""

    added_entity_types: list[str] = Field(default_factory=list)
    removed_entity_types: list[str] = Field(default_factory=list)
    modified_entity_types: list[dict[str, str]] = Field(default_factory=list)
    added_relation_types: list[str] = Field(default_factory=list)
    removed_relation_types: list[str] = Field(default_factory=list)
    modified_relation_types: list[dict[str, str]] = Field(default_factory=list)
