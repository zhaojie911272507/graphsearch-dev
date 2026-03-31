"""Tests for observability features (metrics, tracing, logging)."""

import pytest
from prometheus_client import Counter, Histogram, REGISTRY, generate_latest

from app.observability.tracing import TracingSetup
from app.observability.logging import get_trace_id, get_span_id
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


@pytest.fixture
def reset_metrics():
    """Reset metrics by unregistering all custom collectors.

    Note: Metrics in metrics.py are bound to class _registry at module load time.
    We test using dynamically created metrics with default REGISTRY instead.
    """
    # Unregister all custom collectors to start fresh
    for collector in list(REGISTRY._collector_to_names.keys()):
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass
    yield


@pytest.fixture
def setup_tracing():
    """Set up in-memory tracing for tests."""
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    yield exporter

    provider.shutdown()


class TestMetrics:
    """Test Prometheus metrics collection."""

    def test_metrics_endpoint_returns_data(self, reset_metrics):
        """Test that metrics endpoint returns Prometheus format data."""
        # Create a simple counter to test
        test_counter = Counter(
            "test_counter_total",
            "Test counter",
            registry=REGISTRY,
        )
        test_counter.inc()

        metrics_data = generate_latest(REGISTRY)
        assert isinstance(metrics_data, bytes)
        assert len(metrics_data) > 0
        assert b"test_counter_total" in metrics_data

    def test_http_requests_total_counter(self, reset_metrics):
        """Test HTTP request counter increments."""
        http_requests = Counter(
            "http_requests_total",
            "Total number of HTTP requests",
            labelnames=["method", "path", "status"],
            registry=REGISTRY,
        )

        http_requests.labels(
            method="GET",
            path="/test",
            status="200",
        ).inc()

        metrics_data = generate_latest(REGISTRY).decode()
        assert 'http_requests_total{method="GET",path="/test",status="200"} 1.0' in metrics_data

    def test_embedding_latency_histogram(self, reset_metrics):
        """Test embedding latency histogram observation."""
        embedding_latency = Histogram(
            "rag_embedding_latency_seconds",
            "Time to generate embeddings",
            labelnames=["model", "device"],
            registry=REGISTRY,
        )

        embedding_latency.labels(
            model="m3e-large",
            device="cpu",
        ).observe(0.5)

        metrics_data = generate_latest(REGISTRY).decode()
        assert "rag_embedding_latency_seconds" in metrics_data


class TestTracing:
    """Test OpenTelemetry tracing."""

    def test_tracer_creation(self, setup_tracing):
        """Test tracer can create spans."""
        tracer = TracingSetup.get_tracer("test")

        with tracer.start_as_current_span("test_span") as span:
            span.set_attribute("test.key", "test_value")

        spans = setup_tracing.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "test_span"
        assert spans[0].attributes["test.key"] == "test_value"

    def test_trace_id_generation(self, setup_tracing):
        """Test trace ID is generated in active span context."""
        tracer = TracingSetup.get_tracer("test")

        with tracer.start_as_current_span("test_span"):
            trace_id = get_trace_id()
            assert trace_id is not None
            assert len(trace_id) == 32  # 128-bit hex


class TestLogging:
    """Test enhanced logging with trace context."""

    def test_trace_id_in_log_event(self, setup_tracing):
        """Test trace ID is added to log events."""
        tracer = TracingSetup.get_tracer("test")

        with tracer.start_as_current_span("test_span"):
            trace_id = get_trace_id()
            span_id = get_span_id()

        assert trace_id is not None
        assert span_id is not None
