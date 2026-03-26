"""Audit event models.

Defines the audit event structure and action types for tracking system changes.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel


class AuditAction(str, Enum):
    """Audit action types."""

    # Entity type operations
    ENTITY_TYPE_CREATED = "entity_type.created"
    ENTITY_TYPE_UPDATED = "entity_type.updated"
    ENTITY_TYPE_DELETED = "entity_type.deleted"

    # Relation type operations
    RELATION_TYPE_CREATED = "relation_type.created"
    RELATION_TYPE_UPDATED = "relation_type.updated"
    RELATION_TYPE_DELETED = "relation_type.deleted"

    # Ontology operations
    ONTOLOGY_VERSION_CREATED = "ontology.version.created"
    ONTOLOGY_VERSION_ROLLBACK = "ontology.version.rollback"

    # Configuration operations
    PIPELINE_CONFIG_CREATED = "pipeline.config.created"
    PIPELINE_CONFIG_ACTIVATED = "pipeline.config.activated"
    PROMPT_TEMPLATE_CREATED = "prompt.template.created"
    PROMPT_TEMPLATE_UPDATED = "prompt.template.updated"

    # Other operations
    ANNOTATION_CREATED = "annotation.created"
    VOTE_CAST = "vote.cast"
    EXPLORATION_SAVED = "exploration.saved"


class AuditEvent(BaseModel):
    """Audit event record."""

    id: UUID
    timestamp: datetime
    user_id: str
    action: AuditAction
    resource_type: str  # "entity_type", "relation_type", "pipeline", etc.
    resource_id: str
    changes: dict | None = None
    ip_address: str | None = None
    user_agent: str | None = None
