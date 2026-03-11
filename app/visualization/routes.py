"""Visualization API routes.

Serves graph data and static assets for the graph exploration frontend.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.api.dependencies import GraphStoreDep
from app.persistence.graph_store import GraphStore
from app.visualization.schemas import (
    GraphDataResponse,
    GraphEdgeSchema,
    GraphNodeSchema,
    GraphStatsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/viz", tags=["Visualization"])

# Static assets directory (relative to this file)
_STATIC_DIR = Path(__file__).resolve().parent / "static"


@router.get(
    "/graph",
    response_model=GraphDataResponse,
    summary="Get graph data for visualization",
    description="Returns nodes and edges for the knowledge graph subgraph.",
)
async def get_graph_data(
    store: GraphStoreDep,
    limit: int = 500,
) -> GraphDataResponse:
    """Fetch a subgraph suitable for D3.js or similar visualization libraries."""
    if limit < 1 or limit > 2000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit must be between 1 and 2000",
        )
    try:
        nodes_raw, edges_raw = await store.get_graph_for_visualization(limit=limit)
        nodes = [GraphNodeSchema.model_validate(n) for n in nodes_raw]
        edges = [GraphEdgeSchema.model_validate(e) for e in edges_raw]
        return GraphDataResponse(nodes=nodes, edges=edges)
    except Exception as exc:
        logger.exception("Failed to fetch graph data: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load graph data for visualization",
        ) from exc


@router.get(
    "/stats",
    response_model=GraphStatsResponse,
    summary="Get graph statistics",
)
async def get_graph_stats(store: GraphStoreDep) -> GraphStatsResponse:
    """Return node counts by type."""
    try:
        stats = await store.get_graph_stats()
        # Get relationship count via a simple query if needed
        return GraphStatsResponse(
            document_count=stats.get("Document", 0),
            chunk_count=stats.get("Chunk", 0),
            entity_count=stats.get("Entity", 0),
            concept_count=stats.get("Concept", 0),
            relationship_count=0,  # Optional: add separate query if needed
        )
    except Exception as exc:
        logger.exception("Failed to fetch graph stats: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load graph statistics",
        ) from exc


@router.get(
    "/",
    include_in_schema=False,
)
async def serve_visualization_app() -> FileResponse:
    """Serve the graph visualization single-page application."""
    index_path = _STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visualization frontend not found",
        )
    return FileResponse(index_path)
