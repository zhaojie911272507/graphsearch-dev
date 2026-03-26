"""Domain management models.

A Domain represents a bounded context with its own ontology, configuration,
and extraction rules. Domains can extend a parent domain while adding
domain-specific entity and relation types.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class DomainMetadata(BaseModel):
    """Extensible metadata attached to every domain."""

    model_config = ConfigDict(frozen=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system")
    version: str = Field(default="1.0.0")
    is_active: bool = Field(default=True)


class DomainConfig(BaseModel):
    """Domain-specific configuration settings."""

    model_config = ConfigDict(frozen=True)

    # Extraction settings
    extraction_prompt_template: str = Field(default="")
    max_entity_types: int = Field(default=50, ge=1, le=1000)
    max_relation_types: int = Field(default=100, ge=1, le=2000)

    # Validation rules (stored as JSON-compatible dict)
    validation_rules: dict[str, Any] = Field(default_factory=dict)

    # Inheritance settings
    parent_domain_key: str | None = Field(default=None)
    inherits_base_ontology: bool = Field(default=True)

    def neo4j_properties(self) -> dict[str, object]:
        """Serialize config to Neo4j properties."""
        return {
            "extraction_prompt_template": self.extraction_prompt_template,
            "max_entity_types": self.max_entity_types,
            "max_relation_types": self.max_relation_types,
            "validation_rules": self.validation_rules,
            "parent_domain_key": self.parent_domain_key,
            "inherits_base_ontology": self.inherits_base_ontology,
        }


class Domain(BaseModel):
    """Represents a domain with its schema and configuration.

    A domain encapsulates:
    - A unique key for identification
    - Domain-specific entity and relation types
    - Custom extraction prompts and validation rules
    - Optional inheritance from a parent domain
    """

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=1000)
    domain_key: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-z][a-z0-9_-]*[a-z0-9]$")
    metadata: DomainMetadata = Field(default_factory=DomainMetadata)
    config: DomainConfig = Field(default_factory=DomainConfig)

    # Domain-specific ontology elements (references to type names)
    entity_types: list[str] = Field(default_factory=list)
    relation_types: list[str] = Field(default_factory=list)

    def neo4j_properties(self) -> dict[str, object]:
        """Serialize to a flat dict for Neo4j parameterized queries.

        Returns:
            Property map with string-keyed primitive values.
        """
        props: dict[str, object] = {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "domain_key": self.domain_key,
            "created_at": self.metadata.created_at.isoformat(),
            "updated_at": self.metadata.updated_at.isoformat(),
            "created_by": self.metadata.created_by,
            "version": self.metadata.version,
            "is_active": self.metadata.is_active,
            "entity_types": self.entity_types,
            "relation_types": self.relation_types,
        }

        # Merge config properties
        props.update(self.config.neo4j_properties())

        return props
