"""Pydantic schemas for domain management API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DomainMetadataSchema(BaseModel):
    """Domain metadata for API responses."""

    created_at: datetime
    updated_at: datetime
    created_by: str
    version: str
    is_active: bool


class DomainConfigSchema(BaseModel):
    """Domain configuration for API responses."""

    extraction_prompt_template: str = Field(default="")
    max_entity_types: int = Field(default=50)
    max_relation_types: int = Field(default=100)
    validation_rules: dict[str, Any] = Field(default_factory=dict)
    parent_domain_key: str | None = Field(default=None)
    inherits_base_ontology: bool = Field(default=True)


class DomainSchema(BaseModel):
    """Domain definition for API responses."""

    id: UUID
    name: str
    description: str
    domain_key: str
    metadata: DomainMetadataSchema
    config: DomainConfigSchema
    entity_types: list[str] = Field(default_factory=list)
    relation_types: list[str] = Field(default_factory=list)


class DomainCreateSchema(BaseModel):
    """Request to create a domain."""

    name: str = Field(..., min_length=1, max_length=100, description="Domain display name")
    description: str = Field(default="", max_length=1000, description="Domain description")
    domain_key: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-z][a-z0-9_-]*[a-z0-9]$",
        description="Unique domain identifier (lowercase, alphanumeric, underscores, hyphens)",
    )
    extraction_prompt_template: str = Field(
        default="",
        description="Custom prompt template for entity/relation extraction",
    )
    parent_domain_key: str | None = Field(
        default=None,
        description="Parent domain to inherit from (optional)",
    )
    inherits_base_ontology: bool = Field(
        default=True,
        description="Whether to inherit built-in entity/relation types",
    )


class DomainUpdateSchema(BaseModel):
    """Request to update a domain."""

    name: str | None = None
    description: str | None = None
    extraction_prompt_template: str | None = None
    parent_domain_key: str | None = None
    inherits_base_ontology: bool | None = None


class DomainActivateResponse(BaseModel):
    """Response for domain activation."""

    success: bool
    message: str
    domain_key: str
    activated_at: datetime


class DomainInheritanceChainSchema(BaseModel):
    """Domain inheritance chain for API responses."""

    domain_key: str
    name: str
    inherits_from: str | None


class DomainDiffSchema(BaseModel):
    """Diff between two domains."""

    added_entity_types: list[str] = Field(default_factory=list)
    removed_entity_types: list[str] = Field(default_factory=list)
    added_relation_types: list[str] = Field(default_factory=list)
    removed_relation_types: list[str] = Field(default_factory=list)
    config_changes: dict[str, dict[str, Any]] = Field(default_factory=dict)
