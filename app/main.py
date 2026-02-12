"""FastAPI application entry point.

Manages the application lifecycle (startup/shutdown) and mounts
all route modules. Heavy services are initialized once during
startup and shared via app.state.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import ingest, query
from app.config import Settings, get_settings
from app.domain.schemas import HealthResponse
from app.embedding.service import EmbeddingService
from app.extraction.extractor import GraphExtractor
from app.persistence.graph_store import GraphStore

logger = structlog.get_logger(__name__)


def _configure_logging(settings: Settings) -> None:
    """Configure structlog and stdlib logging."""
    log_level = getattr(logging, settings.app.log_level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if settings.app.app_debug else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle manager.

    Startup:
      1. Load embedding model into memory.
      2. Open Neo4j connection pool.
      3. Ensure database indexes.
      4. Create shared service instances.

    Shutdown:
      1. Close Neo4j connection pool.
      2. Release embedding model memory.
    """
    settings = get_settings()
    _configure_logging(settings)

    log = structlog.get_logger("lifespan")
    await log.ainfo("Starting Graph RAG system", env=settings.app.app_env)

    # Embedding service (singleton)
    embedding_service = EmbeddingService(settings.embedding)
    try:
        embedding_service.load_model()
        await log.ainfo("Embedding model loaded", dimension=settings.embedding.dimension)
    except Exception as exc:
        await log.awarning("Embedding model not loaded — service will be unavailable", error=str(exc))

    # Neo4j connection
    graph_store = GraphStore(settings.neo4j)
    try:
        await graph_store.__aenter__()
        await graph_store.ensure_indexes(dimension=settings.embedding.dimension)
        await log.ainfo("Neo4j connected and indexes ensured")
    except Exception as exc:
        await log.awarning("Neo4j not available — persistence will fail", error=str(exc))

    # Graph extractor
    graph_extractor = GraphExtractor(
        openai_settings=settings.openai,
        extraction_settings=settings.extraction,
    )

    # Store in app state for dependency injection
    app.state.settings = settings
    app.state.embedding_service = embedding_service
    app.state.graph_store = graph_store
    app.state.graph_extractor = graph_extractor

    await log.ainfo("Graph RAG system ready")

    yield

    # Shutdown
    await log.ainfo("Shutting down Graph RAG system")
    await graph_store.__aexit__(None, None, None)
    EmbeddingService.reset()
    await log.ainfo("Shutdown complete")


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app.app_name,
        description="Enterprise Graph RAG System — hybrid vector + graph retrieval with LLM generation",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app.app_debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routes
    app.include_router(ingest.router, prefix="/api/v1")
    app.include_router(query.router, prefix="/api/v1")

    # Health endpoint
    @app.get("/health", response_model=HealthResponse, tags=["System"])
    async def health_check() -> HealthResponse:
        """System health check."""
        neo4j_ok = False
        embedding_ok = False

        try:
            store: GraphStore = app.state.graph_store
            neo4j_ok = await store.check_connectivity()
        except Exception:
            pass

        try:
            service: EmbeddingService = app.state.embedding_service
            embedding_ok = service.is_loaded
        except Exception:
            pass

        return HealthResponse(
            status="ok" if (neo4j_ok and embedding_ok) else "degraded",
            neo4j_connected=neo4j_ok,
            embedding_model_loaded=embedding_ok,
        )

    return app


# Uvicorn entrypoint
app = create_app()
