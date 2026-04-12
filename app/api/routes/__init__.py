"""API route modules."""

from app.api.routes import documents, domains, ingest, metadata, query

__all__ = [
    "documents",
    "domains",
    "ingest",
    "metadata",
    "query",
]