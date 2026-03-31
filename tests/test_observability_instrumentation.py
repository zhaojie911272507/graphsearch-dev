"""Tests for observability instrumentation in embedding and retrieval modules.

Note: These tests verify that the instrumentation code exists and has the correct
structure. Full integration testing of OpenTelemetry spans requires mocking the
TracingSetup.get_tracer() method to return a test tracer.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from app.config import EmbeddingSettings
from app.domain.enums import EntityType, RelationType
from app.domain.schemas import RetrievalContext
from app.embedding.service import EmbeddingService
from app.persistence.graph_store import GraphStore
from app.retrieval.retriever import GraphRetriever


@pytest.fixture
def memory_exporter():
    """Create an in-memory span exporter for testing."""
    return InMemorySpanExporter()


@pytest.fixture
def setup_tracing(memory_exporter):
    """Set up tracing with memory exporter. Call this fixture before testing."""
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(memory_exporter))
    trace.set_tracer_provider(provider)
    return provider


@pytest.fixture
def embedding_settings():
    """Create embedding settings for tests."""
    return EmbeddingSettings(
        model_path="/fake/model/path",
        dimension=1024,
        device="cpu",
    )


@pytest.fixture
def mock_graph_store():
    """Create a mock graph store."""
    store = MagicMock(spec=GraphStore)
    store.vector_search = AsyncMock(return_value=[
        {"node": {"id": "123e4567-e89b-12d3-a456-426614174000", "content": "test", "document_title": "doc", "chunk_index": 0}, "score": 0.95}
    ])
    store.traverse_from_chunks = AsyncMock(return_value=[
        {"neighbor": {"id": "123e4567-e89b-12d3-a456-426614174001", "name": "Entity1", "entity_type": "PERSON"}, "rels": []}
    ])
    return store


class TestEmbeddingServiceInstrumentation:
    """Test embedding service observability instrumentation."""

    @pytest.mark.asyncio
    async def test_embed_query_has_instrumentation_code(self, memory_exporter: InMemorySpanExporter, setup_tracing):
        """Test that embed_query has the instrumentation code structure."""
        # Patch TracingSetup.get_tracer to return our test tracer
        test_tracer = setup_tracing.get_tracer("test")

        settings = EmbeddingSettings(model_path="/test/model", dimension=1024, device="cpu")
        EmbeddingService.reset()

        with patch.object(EmbeddingService, 'embed_documents', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [[0.1] * 1024]

            with patch('app.embedding.service.TracingSetup.get_tracer', return_value=test_tracer):
                service = EmbeddingService(settings)
                result = await service.embed_query("test query")

        # Verify span was created
        spans = memory_exporter.get_finished_spans()
        assert len(spans) > 0, "Expected at least one span to be recorded"

        # Find the embedding span
        embedding_span = None
        for span in spans:
            if span.name == "rag.embedding":
                embedding_span = span
                break

        assert embedding_span is not None, "Expected 'rag.embedding' span"

        # Verify span attributes
        assert embedding_span.attributes.get("embedding.model") == "/test/model"
        assert embedding_span.attributes.get("embedding.device") == "cpu"
        assert embedding_span.attributes.get("embedding.dimension") == 1024
        assert "embedding.duration_seconds" in embedding_span.attributes

    @pytest.mark.asyncio
    async def test_embed_query_records_metrics(self, memory_exporter: InMemorySpanExporter, setup_tracing):
        """Test that embed_query records embedding latency metrics."""
        from app.observability.metrics import MetricsRegistry

        # Reset metrics
        MetricsRegistry.rag_embedding_latency_seconds._metrics = {}

        settings = EmbeddingSettings(model_path="/test/model", dimension=1024, device="cpu")
        EmbeddingService.reset()

        with patch.object(EmbeddingService, 'embed_documents', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [[0.1] * 1024]

            service = EmbeddingService(settings)

            # Call embed_query
            await service.embed_query("test query")

        # Verify metric was recorded
        metrics = MetricsRegistry.generate_metrics()
        assert b"rag_embedding_latency_seconds" in metrics

    @pytest.mark.asyncio
    async def test_embed_query_records_error_span(self, memory_exporter: InMemorySpanExporter, setup_tracing):
        """Test that embed_query records error in span on exception."""
        settings = EmbeddingSettings(model_path="/test/model", dimension=1024, device="cpu")
        EmbeddingService.reset()

        test_tracer = setup_tracing.get_tracer("test")

        with patch.object(EmbeddingService, 'embed_documents', new_callable=AsyncMock) as mock_embed:
            mock_embed.side_effect = Exception("Embedding failed")

            with patch('app.embedding.service.TracingSetup.get_tracer', return_value=test_tracer):
                service = EmbeddingService(settings)

                with pytest.raises(Exception, match="Embedding failed"):
                    await service.embed_query("test query")

        # Verify span with error attribute exists
        spans = memory_exporter.get_finished_spans()
        error_span = None
        for span in spans:
            if span.name == "rag.embedding":
                error_span = span
                break

        assert error_span is not None
        assert error_span.attributes.get("error") is True
        assert len(error_span.events) > 0  # Should have exception event


class TestGraphRetrieverInstrumentation:
    """Test graph retriever observability instrumentation."""

    @pytest.mark.asyncio
    async def test_retrieve_records_tracing_spans(
        self,
        memory_exporter: InMemorySpanExporter,
        setup_tracing,
        mock_graph_store: MagicMock,
    ):
        """Test that retrieve creates tracing spans with correct attributes."""
        settings = EmbeddingSettings(model_path="/test/model", dimension=1024, device="cpu")
        EmbeddingService.reset()

        test_tracer = setup_tracing.get_tracer("test")

        with patch.object(EmbeddingService, 'embed_documents', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [[0.1] * 1024]

            embedder = EmbeddingService(settings)

            retriever = GraphRetriever(
                graph_store=mock_graph_store,
                embedding_service=embedder,
            )

            with patch('app.retrieval.retriever.TracingSetup.get_tracer', return_value=test_tracer):
                # Call retrieve
                await retriever.retrieve("test query", top_k=5, traversal_depth=2)

        # Verify spans were created
        spans = memory_exporter.get_finished_spans()
        span_names = [span.name for span in spans]

        assert "rag.retrieval" in span_names, "Expected 'rag.retrieval' span"
        assert "rag.vector_search" in span_names, "Expected 'rag.vector_search' span"
        assert "rag.graph_traversal" in span_names, "Expected 'rag.graph_traversal' span"

        # Verify retrieval span attributes
        retrieval_span = next(s for s in spans if s.name == "rag.retrieval")
        assert retrieval_span.attributes.get("rag.query") == "test query"
        assert retrieval_span.attributes.get("rag.top_k") == 5
        assert retrieval_span.attributes.get("rag.traversal_depth") == 2
        assert retrieval_span.attributes.get("rag.mode") == "hybrid"
        assert retrieval_span.attributes.get("rag.total_duration_ms") is not None

    @pytest.mark.asyncio
    async def test_retrieve_records_vector_only_mode(
        self,
        memory_exporter: InMemorySpanExporter,
        setup_tracing,
        mock_graph_store: MagicMock,
    ):
        """Test that retrieve in vector_only mode skips graph traversal span."""
        settings = EmbeddingSettings(model_path="/test/model", dimension=1024, device="cpu")
        EmbeddingService.reset()

        test_tracer = setup_tracing.get_tracer("test")

        with patch.object(EmbeddingService, 'embed_documents', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [[0.1] * 1024]

            embedder = EmbeddingService(settings)

            retriever = GraphRetriever(
                graph_store=mock_graph_store,
                embedding_service=embedder,
            )

            with patch('app.retrieval.retriever.TracingSetup.get_tracer', return_value=test_tracer):
                # Call retrieve in vector_only mode
                await retriever.retrieve("test query", top_k=5, vector_only=True)

        # Verify spans
        spans = memory_exporter.get_finished_spans()
        span_names = [span.name for span in spans]

        assert "rag.retrieval" in span_names
        assert "rag.vector_search" in span_names
        assert "rag.graph_traversal" not in span_names  # Skipped in vector_only

        # Verify mode attribute
        retrieval_span = next(s for s in spans if s.name == "rag.retrieval")
        assert retrieval_span.attributes.get("rag.mode") == "vector_only"

    @pytest.mark.asyncio
    async def test_retrieve_records_metrics(
        self,
        mock_graph_store: MagicMock,
    ):
        """Test that retrieve records retrieval metrics."""
        from app.observability.metrics import MetricsRegistry

        # Reset metrics
        MetricsRegistry.rag_vector_search_latency_seconds._metrics = {}
        MetricsRegistry.rag_graph_traversal_latency_seconds._metrics = {}
        MetricsRegistry.rag_retrieval_total_chunks._metrics = {}

        settings = EmbeddingSettings(model_path="/test/model", dimension=1024, device="cpu")
        EmbeddingService.reset()

        with patch.object(EmbeddingService, 'embed_documents', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [[0.1] * 1024]

            embedder = EmbeddingService(settings)

            retriever = GraphRetriever(
                graph_store=mock_graph_store,
                embedding_service=embedder,
            )

            # Call retrieve
            await retriever.retrieve("test query", top_k=10, traversal_depth=2)

        # Verify metrics recorded
        metrics = MetricsRegistry.generate_metrics()
        assert b"rag_vector_search_latency_seconds" in metrics
        assert b"rag_graph_traversal_latency_seconds" in metrics
        assert b"rag_retrieval_total_chunks" in metrics

    @pytest.mark.asyncio
    async def test_retrieve_records_vector_search_duration(
        self,
        memory_exporter: InMemorySpanExporter,
        setup_tracing,
        mock_graph_store: MagicMock,
    ):
        """Test that vector search span records duration attribute."""
        settings = EmbeddingSettings(model_path="/test/model", dimension=1024, device="cpu")
        EmbeddingService.reset()

        test_tracer = setup_tracing.get_tracer("test")

        with patch.object(EmbeddingService, 'embed_documents', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [[0.1] * 1024]

            embedder = EmbeddingService(settings)

            retriever = GraphRetriever(
                graph_store=mock_graph_store,
                embedding_service=embedder,
            )

            with patch('app.retrieval.retriever.TracingSetup.get_tracer', return_value=test_tracer):
                await retriever.retrieve("test query", top_k=5)

        spans = memory_exporter.get_finished_spans()
        vector_span = next((s for s in spans if s.name == "rag.vector_search"), None)

        assert vector_span is not None
        assert "vector_search.duration_ms" in vector_span.attributes

    @pytest.mark.asyncio
    async def test_retrieve_records_graph_traversal_duration(
        self,
        memory_exporter: InMemorySpanExporter,
        setup_tracing,
        mock_graph_store: MagicMock,
    ):
        """Test that graph traversal span records duration and depth attributes."""
        settings = EmbeddingSettings(model_path="/test/model", dimension=1024, device="cpu")
        EmbeddingService.reset()

        test_tracer = setup_tracing.get_tracer("test")

        with patch.object(EmbeddingService, 'embed_documents', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [[0.1] * 1024]

            embedder = EmbeddingService(settings)

            retriever = GraphRetriever(
                graph_store=mock_graph_store,
                embedding_service=embedder,
            )

            with patch('app.retrieval.retriever.TracingSetup.get_tracer', return_value=test_tracer):
                await retriever.retrieve("test query", top_k=5, traversal_depth=3)

        spans = memory_exporter.get_finished_spans()
        graph_span = next((s for s in spans if s.name == "rag.graph_traversal"), None)

        assert graph_span is not None
        assert graph_span.attributes.get("graph_traversal.duration_ms") is not None
        assert graph_span.attributes.get("graph_traversal.depth") == 3


class TestMetricsIntegration:
    """Test metrics integration across embedding and retrieval."""

    @pytest.mark.asyncio
    async def test_embedding_metrics_labels(self, memory_exporter: InMemorySpanExporter, setup_tracing):
        """Test that embedding metrics have correct labels."""
        from app.observability.metrics import MetricsRegistry

        # Reset
        MetricsRegistry.rag_embedding_latency_seconds._metrics = {}

        settings = EmbeddingSettings(model_path="m3e-large", dimension=1024, device="cpu")
        EmbeddingService.reset()

        with patch.object(EmbeddingService, 'embed_documents', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [[0.1] * 1024]

            service = EmbeddingService(settings)

            await service.embed_query("test")

        # Verify metric can be accessed with correct labels
        metrics = MetricsRegistry.generate_metrics()
        assert b'model="m3e-large"' in metrics or b"m3e-large" in metrics

    @pytest.mark.asyncio
    async def test_retrieval_metrics_by_mode(
        self,
        memory_exporter: InMemorySpanExporter,
        setup_tracing,
        mock_graph_store: MagicMock,
    ):
        """Test that retrieval metrics are labeled by mode."""
        from app.observability.metrics import MetricsRegistry

        settings = EmbeddingSettings(model_path="/test/model", dimension=1024, device="cpu")
        EmbeddingService.reset()

        with patch.object(EmbeddingService, 'embed_documents', new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [[0.1] * 1024]

            embedder = EmbeddingService(settings)

            retriever = GraphRetriever(
                graph_store=mock_graph_store,
                embedding_service=embedder,
            )

            # Test hybrid mode
            MetricsRegistry.rag_retrieval_total_chunks._metrics = {}
            await retriever.retrieve("test", vector_only=False)

            metrics = MetricsRegistry.generate_metrics()
            assert b'mode="hybrid"' in metrics or b"hybrid" in metrics

            # Test vector_only mode
            MetricsRegistry.rag_retrieval_total_chunks._metrics = {}
            await retriever.retrieve("test", vector_only=True)

            metrics = MetricsRegistry.generate_metrics()
            assert b'mode="vector_only"' in metrics or b"vector_only" in metrics
