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
from fastapi.responses import RedirectResponse

from app.api.routes import ingest, query
from app.api.routes import metadata, ontology, intelligence, evaluation, domains, audit, documents, simulation
from app.api.routes import simulation_exec, simulation_report, simulation_dialogue
from app.api.routes import auth, temporal
from app.visualization.routes import router as viz_router
from app.config import Settings, get_settings
from app.observability.metrics import MetricsRegistry
from app.observability.tracing import TracingSetup
from app.observability.logging import setup_enhanced_logging
from app.domain.schemas import HealthResponse
from app.embedding.service import EmbeddingService
from app.extraction.extractor import GraphExtractor
from app.persistence.graph_store import GraphStore
from app.persistence.temporal_store import TemporalStore
from app.services.temporal_knowledge.version_manager import VersionManager
from app.services.temporal_knowledge.summary_generator import SummaryGenerator
from app.services.temporal_knowledge.batch_merger import BatchMerger
from app.api.routes.temporal import set_temporal_services

logger = structlog.get_logger(__name__)


def _configure_logging(settings: Settings) -> None:
    """Configure structlog and stdlib logging."""
    # Use enhanced logging with trace context
    setup_enhanced_logging(debug=settings.app.app_debug)


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

    # Initialize OpenTelemetry tracing
    TracingSetup.initialize(settings)

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

    # Temporal services
    temporal_store = None
    version_manager = None
    summary_generator = None
    batch_merger = None

    if graph_store._driver:
        try:
            # Create temporal store
            temporal_store = TemporalStore(graph_store._driver)
            await temporal_store.create_indexes()

            # Create version manager
            version_manager = VersionManager(temporal_store)

            # Create summary generator
            summary_generator = SummaryGenerator(
                openai_settings=settings.openai,
                temporal_settings=settings.temporal,
            )
            summary_generator.set_version_manager(version_manager)
            summary_generator.set_temporal_store(temporal_store)

            # Create batch merger and start scheduler
            batch_merger = BatchMerger(
                temporal_settings=settings.temporal,
                version_manager=version_manager,
                summary_generator=summary_generator,
            )
            await batch_merger.start()

            # Set global services for API routes
            set_temporal_services(
                temporal_store=temporal_store,
                version_manager=version_manager,
                summary_generator=summary_generator,
                batch_merger=batch_merger,
            )

            await log.ainfo("Temporal services initialized")
        except Exception as exc:
            await log.awarning("Temporal services failed to initialize", error=str(exc))

    # Store in app state for dependency injection
    app.state.settings = settings
    app.state.embedding_service = embedding_service
    app.state.graph_store = graph_store
    app.state.graph_extractor = graph_extractor

    await log.ainfo("Graph RAG system ready")

    yield

    # Shutdown
    await log.ainfo("Shutting down Graph RAG system")

    # Stop batch merger
    if batch_merger:
        await batch_merger.stop()

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
    app.include_router(ontology.router, prefix="/api/v1")
    app.include_router(intelligence.router, prefix="/api/v1")
    app.include_router(evaluation.router, prefix="/api/v1")
    app.include_router(domains.router, prefix="/api/v1")
    app.include_router(audit.router, prefix="/api/v1")
    app.include_router(documents.router, prefix="/api/v1")
    app.include_router(simulation.router, prefix="/api/v1")
    app.include_router(simulation_exec.router, prefix="/api/v1")
    app.include_router(simulation_report.router, prefix="/api/v1")
    app.include_router(simulation_dialogue.router, prefix="/api/v1")
    app.include_router(temporal.router, prefix="/api/v1")
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
        from fastapi.responses import Response
        from prometheus_client import CONTENT_TYPE_LATEST

        settings = get_settings()
        if not settings.observability.metrics_enabled:
            return Response(status_code=503, content="Metrics disabled")

        return Response(
            content=MetricsRegistry.generate_metrics(),
            media_type=CONTENT_TYPE_LATEST,
        )

    # Instrument FastAPI with OpenTelemetry
    TracingSetup.instrument_app(app)

    return app


# Uvicorn entrypoint
app = create_app()
