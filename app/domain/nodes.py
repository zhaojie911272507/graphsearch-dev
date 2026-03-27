"""Graph node domain models.

Every node inherits from BaseNode which provides a UUID primary key
and immutable metadata. These Pydantic models serve as the canonical
contract between the application layer and the Neo4j persistence layer.
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import EntityType, NodeType


class NodeMetadata(BaseModel):
    """Extensible metadata attached to every graph node."""

    model_config = ConfigDict(frozen=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(default="system")
    tags: tuple[str, ...] = Field(default=())


class BaseNode(BaseModel):
    """Abstract base for all graph nodes.

    Provides identity (UUID), type discriminator, and metadata.
    All concrete node types MUST inherit from this.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4, description="Unique node identifier")
    node_type: NodeType
    metadata: NodeMetadata = Field(default_factory=NodeMetadata)

    def neo4j_properties(self) -> dict[str, object]:
        """Serialize to a flat dict suitable for Neo4j parameter injection.

        Returns:
            Property map with string-keyed primitive values.
        """
        props: dict[str, object] = {
            "id": str(self.id),
            "node_type": self.node_type.value,
            "created_at": self.metadata.created_at.isoformat(),
            "updated_at": self.metadata.updated_at.isoformat(),
            "source": self.metadata.source,
        }
        return props


class DocumentNode(BaseNode):
    """Represents an ingested source document."""

    node_type: NodeType = Field(default=NodeType.DOCUMENT, frozen=True)
    title: str = Field(..., min_length=1, max_length=500)
    source_url: str = Field(default="")
    content_hash: str = Field(
        default="",
        description="SHA-256 hash of raw content for deduplication",
    )
    # File upload metadata
    filename: str = Field(default="", description="Original uploaded filename")
    file_size: int = Field(default=0, description="File size in bytes")
    file_type: str = Field(default="", description="MIME type (pdf, docx, txt)")
    upload_status: str = Field(default="pending", description="pending/processing/complete/failed")
    parse_error: str | None = Field(default=None, description="Error message if parsing failed")

    def neo4j_properties(self) -> dict[str, object]:
        props = super().neo4j_properties()
        props.update(
            {
                "title": self.title,
                "source_url": self.source_url,
                "content_hash": self.content_hash,
                "filename": self.filename,
                "file_size": self.file_size,
                "file_type": self.file_type,
                "upload_status": self.upload_status,
                "parse_error": self.parse_error,
            }
        )
        return props


class ChunkNode(BaseNode):
    """Represents a text chunk derived from a Document.

    The embedding field stores the dense vector produced by the
    local M3E-Large model (dimension=1024).

    Enhanced with MiroFish-style semantic chunking metadata:
    - section_title: Optional section/heading this chunk belongs to
    - paragraph_type: Type of content (paragraph, list, code, table, etc.)
    - word_count: Number of words in the chunk
    - sentence_count: Number of sentences in the chunk
    - semantic_boundary_start: Whether this chunk starts at a semantic boundary
    - semantic_boundary_end: Whether this chunk ends at a semantic boundary
    """

    node_type: NodeType = Field(default=NodeType.CHUNK, frozen=True)
    content: str = Field(..., min_length=1)
    chunk_index: int = Field(..., ge=0)
    document_id: UUID = Field(..., description="Parent document reference")
    embedding: tuple[float, ...] = Field(
        default=(),
        description="Dense vector from embedding model",
    )
    # MiroFish-style semantic metadata
    section_title: str = Field(default="", description="Section or heading this chunk belongs to")
    paragraph_type: str = Field(default="paragraph", description="Type: paragraph/list/code/table/header")
    word_count: int = Field(default=0, description="Number of words in chunk")
    sentence_count: int = Field(default=0, description="Number of sentences in chunk")
    semantic_boundary_start: bool = Field(default=True, description="Whether chunk starts at semantic boundary")
    semantic_boundary_end: bool = Field(default=True, description="Whether chunk ends at semantic boundary")
    previous_chunk_overlap: str = Field(default="", description="Text overlap from previous chunk")

    @field_validator("embedding")
    @classmethod
    def validate_embedding_dimension(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        """Enforce embedding dimension when present.

        The M3E-Large model outputs 1024-dimensional vectors.
        Empty tuple is permitted for pre-embedding state.
        """
        if len(v) > 0 and len(v) != 1024:
            msg = f"Embedding dimension must be 1024, got {len(v)}"
            raise ValueError(msg)
        return v

    def neo4j_properties(self) -> dict[str, object]:
        props = super().neo4j_properties()
        props.update(
            {
                "content": self.content,
                "chunk_index": self.chunk_index,
                "document_id": str(self.document_id),
                "embedding": list(self.embedding) if self.embedding else [],
                "section_title": self.section_title,
                "paragraph_type": self.paragraph_type,
                "word_count": self.word_count,
                "sentence_count": self.sentence_count,
                "semantic_boundary_start": self.semantic_boundary_start,
                "semantic_boundary_end": self.semantic_boundary_end,
                "previous_chunk_overlap": self.previous_chunk_overlap,
            }
        )
        return props


class EntityNode(BaseNode):
    """Represents a named entity extracted from text.

    When entity_deduplication is enabled, entities are merged by name + entity_type
    across documents, and reference_count tracks how many documents reference this entity.
    """

    node_type: NodeType = Field(default=NodeType.ENTITY, frozen=True)
    name: str = Field(..., min_length=1, max_length=300)
    entity_type: EntityType = Field(...)
    description: str = Field(default="")
    reference_count: int = Field(default=1, description="Number of documents referencing this entity")
    source_document_ids: list[str] = Field(default_factory=list, description="List of document IDs referencing this entity")

    def neo4j_properties(self) -> dict[str, object]:
        props = super().neo4j_properties()
        props.update(
            {
                "name": self.name,
                "entity_type": self.entity_type.value,
                "description": self.description,
                "reference_count": self.reference_count,
                "source_document_ids": self.source_document_ids,
            }
        )
        return props


class ConceptNode(BaseNode):
    """Represents an abstract concept or topic.

    When concept_deduplication is enabled, concepts are merged by name
    across documents, and reference_count tracks how many documents reference this concept.
    """

    node_type: NodeType = Field(default=NodeType.CONCEPT, frozen=True)
    name: str = Field(..., min_length=1, max_length=300)
    definition: str = Field(default="")
    reference_count: int = Field(default=1, description="Number of documents referencing this concept")
    source_document_ids: list[str] = Field(default_factory=list, description="List of document IDs referencing this concept")

    def neo4j_properties(self) -> dict[str, object]:
        props = super().neo4j_properties()
        props.update(
            {
                "name": self.name,
                "definition": self.definition,
                "reference_count": self.reference_count,
                "source_document_ids": self.source_document_ids,
            }
        )
        return props


# Type alias for polymorphic node handling
GraphNode = DocumentNode | ChunkNode | EntityNode | ConceptNode
