"""FastAPI dependency injection factories.

All heavy services (GraphStore, EmbeddingService, GraphExtractor, GraphRetriever)
are provided via Depends() to ensure singleton reuse and testability.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.embedding.service import EmbeddingService
from app.extraction.extractor import GraphExtractor
from app.persistence.graph_store import GraphStore
from app.retrieval.retriever import GraphRetriever


def get_app_settings() -> Settings:
    """Provide validated application settings."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_app_settings)]


async def get_graph_store(request: Request) -> AsyncGenerator[GraphStore, None]:
    """Provide the shared GraphStore instance from app state.

    The GraphStore is opened during lifespan startup and closed on shutdown.
    This dependency simply yields the already-connected instance.
    """
    store: GraphStore = request.app.state.graph_store
    yield store


GraphStoreDep = Annotated[GraphStore, Depends(get_graph_store)]


async def get_embedding_service(request: Request) -> EmbeddingService:
    """Provide the shared EmbeddingService singleton from app state."""
    service: EmbeddingService = request.app.state.embedding_service
    return service


EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service)]


async def get_graph_extractor(request: Request) -> GraphExtractor:
    """Provide the GraphExtractor (created during lifespan)."""
    extractor: GraphExtractor = request.app.state.graph_extractor
    return extractor


GraphExtractorDep = Annotated[GraphExtractor, Depends(get_graph_extractor)]


async def get_graph_retriever(
    store: GraphStoreDep,
    embedder: EmbeddingServiceDep,
) -> GraphRetriever:
    """Compose a GraphRetriever from its dependencies."""
    return GraphRetriever(graph_store=store, embedding_service=embedder)


GraphRetrieverDep = Annotated[GraphRetriever, Depends(get_graph_retriever)]


async def get_embedding_service(request: Request) -> EmbeddingService:
    """Provide the shared EmbeddingService singleton from app state."""
    service: EmbeddingService = request.app.state.embedding_service
    return service


EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service)]


async def get_graph_extractor(request: Request) -> GraphExtractor:
    """Provide the GraphExtractor (created during lifespan)."""
    extractor: GraphExtractor = request.app.state.graph_extractor
    return extractor


GraphExtractorDep = Annotated[GraphExtractor, Depends(get_graph_extractor)]


async def get_graph_retriever(
    store: GraphStoreDep,
    embedder: EmbeddingServiceDep,
) -> GraphRetriever:
    """Compose a GraphRetriever from its dependencies."""
    return GraphRetriever(graph_store=store, embedding_service=embedder)


GraphRetrieverDep = Annotated[GraphRetriever, Depends(get_graph_retriever)]
