"""Custom exception hierarchy for the Graph RAG system.

All domain-specific exceptions inherit from GraphRAGError to enable
granular catching while still supporting a top-level catch-all.
"""

from typing import Any


class GraphRAGError(Exception):
    """Base exception for all Graph RAG system errors."""

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


# ──────────────────────────────────────────
# Persistence Layer
# ──────────────────────────────────────────


class Neo4jConnectionError(GraphRAGError):
    """Raised when the Neo4j connection cannot be established or is lost."""


class Neo4jQueryError(GraphRAGError):
    """Raised when a Cypher query fails at execution time."""


class Neo4jTransactionError(GraphRAGError):
    """Raised when a transaction commit or rollback fails."""


# ──────────────────────────────────────────
# Embedding Layer
# ──────────────────────────────────────────


class EmbeddingModelLoadError(GraphRAGError):
    """Raised when the local embedding model fails to load."""


class EmbeddingDimensionMismatchError(GraphRAGError):
    """Raised when an embedding vector has an unexpected dimension."""


# ──────────────────────────────────────────
# Extraction Layer
# ──────────────────────────────────────────


class ExtractionError(GraphRAGError):
    """Base exception for extraction pipeline failures."""


class LLMExtractionError(ExtractionError):
    """Raised when the LLM fails to produce a valid extraction result."""


class LLMResponseParsingError(ExtractionError):
    """Raised when LLM output cannot be parsed into the expected schema."""


class ExtractionTimeoutError(ExtractionError):
    """Raised when extraction exceeds the configured timeout."""


# ──────────────────────────────────────────
# Retrieval Layer
# ──────────────────────────────────────────


class RetrievalError(GraphRAGError):
    """Base exception for retrieval engine failures."""


class VectorSearchError(RetrievalError):
    """Raised when the vector similarity search fails."""


class GraphTraversalError(RetrievalError):
    """Raised when graph traversal encounters an error."""


# ──────────────────────────────────────────
# Ingestion / API Layer
# ──────────────────────────────────────────


class IngestionError(GraphRAGError):
    """Raised when the document ingestion pipeline fails."""


class DocumentAlreadyExistsError(IngestionError):
    """Raised when attempting to ingest a document that already exists."""


class InvalidDocumentError(IngestionError):
    """Raised when the submitted document is malformed or empty."""
