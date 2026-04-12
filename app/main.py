"""FastAPI application entry point.

Manages the application lifecycle (startup/shutdown) and mounts
all route modules. Heavy services are initialized once during
startup and shared via app.state.
"""

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import (
    auth,
    documents,
    domains,
    ingest,
    metadata,
    query,
)
from app.config import Settings, get_settings
from app.domain.schemas import HealthResponse
from app.embedding.service import EmbeddingService
from app.extraction.extractor import GraphExtractor
from app.observability.logging import setup_enhanced_logging
from app.observability.metrics import MetricsRegistry
from app.observability.tracing import TracingSetup
from app.persistence.graph_store import GraphStore
from app.visualization.routes import router as viz_router

logger = structlog.get_logger(__name__)


def _configure_logging(settings: Settings) -> None:
    """Configure structlog and stdlib logging."""
    setup_enhanced_logging(
        debug=settings.app.app_debug,
        log_level=settings.app.log_level,
    )


# Simple in-memory rate limiter middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple token bucket rate limiter."""

    def __init__(self, app, requests_per_minute: int = 60, burst: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst = burst
        self.buckets: dict[str, dict] = {}  # ip -> {tokens, last_update}

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/metrics", "/docs", "/openapi.json", "/viz/"]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Initialize or update bucket
        if client_ip not in self.buckets:
            self.buckets[client_ip] = {
                "tokens": self.burst,
                "last_update": current_time
            }

        bucket = self.buckets[client_ip]
        # Refill tokens based on time elapsed
        elapsed = current_time - bucket["last_update"]
        bucket["tokens"] = min(
            self.burst,
            bucket["tokens"] + elapsed * (self.requests_per_minute / 60.0)
        )
        bucket["last_update"] = current_time

        # Check if request allowed
        if bucket["tokens"] < 1:
            return Response(
                content='{"detail":"Rate limit exceeded. Please try again later."}',
                status_code=429,
                media_type="application/json"
            )

        # Consume token
        bucket["tokens"] -= 1

        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
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

    TracingSetup.initialize(settings)

    log = structlog.get_logger("lifespan")
    await log.ainfo("Starting Graph RAG system", env=settings.app.app_env)

    TracingSetup.instrument_app(app)

    # Embedding service (singleton)
    embedding_service = EmbeddingService(settings.embedding)
    try:
        embedding_service.load_model()
        await log.ainfo("Embedding model loaded", dimension=settings.embedding.dimension)
    except Exception as exc:
        await log.awarning("Embedding model not loaded — service will be unavailable", error=str(exc))

    # Neo4j connection
    graph_store = GraphStore(settings.neo4j, retrieval_settings=settings.retrieval)
    try:
        await graph_store.__aenter__()
        await graph_store.ensure_indexes(dimension=settings.embedding.dimension)
        # Initialize built-in ontology types
        await graph_store.ensure_builtin_ontology_types()
        await log.ainfo("Built-in ontology types initialized")
        if settings.app.domain_auto_bootstrap:
            try:
                await graph_store.ensure_default_active_domain(
                    default_domain_key=settings.app.default_domain_key,
                    default_name=settings.app.default_domain_name,
                )
                await log.ainfo("Active domain ensured (bootstrap)")
            except Exception as boot_exc:
                await log.awarning(
                    "Domain auto-bootstrap failed — GET /domains/active may return 404 until a domain exists",
                    error=str(boot_exc),
                )
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
    TracingSetup.shutdown()
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

    if settings.app.rate_limit_enabled:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=settings.app.rate_limit_requests_per_minute,
            burst=settings.app.rate_limit_burst,
        )

    # Root redirect to visualization
    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        """Redirect root to the graph visualization frontend."""
        return RedirectResponse(url="/viz/", status_code=302)

    # Mount routes
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(ingest.router, prefix="/api/v1")
    app.include_router(query.router, prefix="/api/v1")
    app.include_router(metadata.router, prefix="/api/v1")
    app.include_router(domains.router, prefix="/api/v1")
    app.include_router(documents.router, prefix="/api/v1")
    app.include_router(viz_router)

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

    # Metrics endpoint
    @app.get("/metrics", tags=["Observability"])
    async def metrics():
        """Prometheus metrics endpoint."""
        settings = get_settings()
        if not settings.observability.metrics_enabled:
            return Response(status_code=503, content="Metrics disabled")

        return Response(
            content=MetricsRegistry.generate_metrics(),
            media_type=CONTENT_TYPE_LATEST,
        )

    return app


# Uvicorn entrypoint
app = create_app()
