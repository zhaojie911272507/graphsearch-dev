"""Domain enumerations for the Graph RAG ontology.

These enums serve as the single source of truth for node types,
relationship types, and entity classifications across the system.
"""

from enum import StrEnum


class NodeType(StrEnum):
    """Graph node labels matching the Neo4j schema."""

    DOCUMENT = "Document"
    CHUNK = "Chunk"
    ENTITY = "Entity"
    CONCEPT = "Concept"
    ENTITY_VERSION = "EntityVersion"
    RELATIONSHIP_SNAPSHOT = "RelationshipSnapshot"


class EntityType(StrEnum):
    """Named entity classifications extracted by the LLM."""

    PERSON = "PERSON"
    ORGANIZATION = "ORG"
    LOCATION = "LOCATION"
    EVENT = "EVENT"
    TECHNOLOGY = "TECHNOLOGY"
    PRODUCT = "PRODUCT"
    DATE = "DATE"
    OTHER = "OTHER"


class RelationType(StrEnum):
    """Typed relationships between graph nodes."""

    HAS_CHUNK = "HAS_CHUNK"
    MENTIONS = "MENTIONS"
    RELATED_TO = "RELATED_TO"
    BELONGS_TO = "BELONGS_TO"
    DEFINES = "DEFINES"
