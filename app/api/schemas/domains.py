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
    """Domain configuration for API responses.

    Domain acts as a namespace isolation layer. It does not contain
    entity/relation types - those are managed globally via Ontology.
    """

    parent_domain_key: str | None = Field(default=None)
    inherits_base_ontology: bool = Field(
        default=True,
        description="Whether to inherit built-in entity/relation types from base ontology",
    )


class DomainSchema(BaseModel):
    """Domain definition for API responses.

    Domain is a namespace isolation layer for grouping assets.
    Entity types and relation types are managed globally via Ontology API.
    """

    id: UUID
    name: str
    description: str
    domain_key: str
    metadata: DomainMetadataSchema
    config: DomainConfigSchema


class DomainCreateSchema(BaseModel):
    """Request to create a domain.

    Domain provides namespace isolation. It does not define entity/relation types.
    Use Ontology API to manage types globally.
    """

    name: str = Field(..., min_length=1, max_length=100, description="Domain display name")
    description: str = Field(default="", max_length=1000, description="Domain description")
    domain_key: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-z][a-z0-9_-]*[a-z0-9]$",
        description="Unique domain identifier (lowercase, alphanumeric, underscores, hyphens)",
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
    extraction_prompt_template: str | None = Field(
        default=None,
        description="Optional per-domain extraction prompt override",
    )
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
