"""API request/response schemas (Pydantic v2).

These models define the external contract of the API and are decoupled
from the internal domain models. Conversion methods are provided where needed.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import EntityType, RelationType


# ──────────────────────────────────────────
# Ingestion
# ──────────────────────────────────────────


class IngestRequest(BaseModel):
    """Request body for POST /ingest."""

    model_config = ConfigDict(frozen=True)

    title: str = Field(..., min_length=1, max_length=500, examples=["Quarterly Report Q3"])
    content: str = Field(..., min_length=1, description="Raw document text")
    source_url: str = Field(default="", examples=["https://example.com/report.pdf"])
    tags: list[str] = Field(default_factory=list)


class IngestResponse(BaseModel):
    """Response body for POST /ingest."""

    document_id: UUID
    chunk_count: int
    entity_count: int
    relationship_count: int
    message: str = Field(default="Document ingested successfully")


# ──────────────────────────────────────────
# Query
# ──────────────────────────────────────────


class QueryRequest(BaseModel):
    """Request body for POST /query."""

    model_config = ConfigDict(frozen=True)

    question: str = Field(..., min_length=1, max_length=2000, examples=["What is Graph RAG?"])
    top_k: int = Field(default=10, ge=1, le=100)
    traversal_depth: int = Field(default=2, ge=1, le=5)
    include_sources: bool = Field(default=True)


class RetrievedChunk(BaseModel):
    """A single chunk returned from the retrieval engine."""

    chunk_id: UUID
    content: str
    score: float = Field(ge=0.0, le=1.0)
    document_title: str = Field(default="")
    chunk_index: int = Field(ge=0)


class RetrievedEntity(BaseModel):
    """An entity discovered during graph traversal."""

    entity_id: UUID
    name: str
    entity_type: EntityType


class RetrievedRelation(BaseModel):
    """A relationship discovered during graph traversal."""

    source_name: str
    target_name: str
    relation_type: RelationType
    weight: float


class RetrievalContext(BaseModel):
    """Aggregated retrieval context fed to the LLM for generation."""

    chunks: list[RetrievedChunk] = Field(default_factory=list)
    entities: list[RetrievedEntity] = Field(default_factory=list)
    relations: list[RetrievedRelation] = Field(default_factory=list)

    @property
    def formatted_context(self) -> str:
        """Format the retrieval results into a text block for LLM prompting."""
        parts: list[str] = []

        if self.chunks:
            parts.append("=== Relevant Text Chunks ===")
            for c in self.chunks:
                parts.append(f"[Chunk {c.chunk_index} | score={c.score:.3f}] {c.content}")

        if self.entities:
            parts.append("\n=== Discovered Entities ===")
            for e in self.entities:
                parts.append(f"- {e.name} ({e.entity_type})")

        if self.relations:
            parts.append("\n=== Graph Relations ===")
            for r in self.relations:
                parts.append(f"- {r.source_name} --[{r.relation_type}]--> {r.target_name}")

        return "\n".join(parts)


class QueryResponse(BaseModel):
    """Response body for POST /query."""

    answer: str
    context: RetrievalContext | None = None
    model: str = Field(default="")
    latency_ms: float = Field(ge=0.0)


# ──────────────────────────────────────────
# Health / Status
# ──────────────────────────────────────────


class HealthResponse(BaseModel):
    """System health check response."""

    status: str = Field(default="ok")
    neo4j_connected: bool = Field(default=False)
    embedding_model_loaded: bool = Field(default=False)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
