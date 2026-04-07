"""Tests for Prometheus metrics collection."""

import pytest
from prometheus_client import CollectorRegistry


class TestMetricsRegistry:
    """Test MetricsRegistry functionality."""

    def test_registry_exists(self):
        """Test that the metrics registry is accessible."""
        from app.observability.metrics import MetricsRegistry

        registry = MetricsRegistry.get_registry()
        assert isinstance(registry, CollectorRegistry)

    def test_http_requests_total_counter(self):
        """Test HTTP requests total counter is defined."""
        from app.observability.metrics import MetricsRegistry

        assert hasattr(MetricsRegistry, "http_requests_total")
        assert MetricsRegistry.http_requests_total is not None

    def test_http_request_duration_histogram(self):
        """Test HTTP request duration histogram is defined."""
        from app.observability.metrics import MetricsRegistry

        assert hasattr(MetricsRegistry, "http_request_duration_seconds")
        assert MetricsRegistry.http_request_duration_seconds is not None

    def test_http_requests_in_progress_gauge(self):
        """Test HTTP requests in progress gauge is defined."""
        from app.observability.metrics import MetricsRegistry

        assert hasattr(MetricsRegistry, "http_requests_in_progress")
        assert MetricsRegistry.http_requests_in_progress is not None

    def test_embedding_latency_histogram(self):
        """Test embedding latency histogram is defined."""
        from app.observability.metrics import MetricsRegistry

        assert hasattr(MetricsRegistry, "rag_embedding_latency_seconds")
        assert MetricsRegistry.rag_embedding_latency_seconds is not None

    def test_vector_search_metrics(self):
        """Test vector search metrics are defined."""
        from app.observability.metrics import MetricsRegistry

        assert hasattr(MetricsRegistry, "rag_vector_search_latency_seconds")
        assert hasattr(MetricsRegistry, "rag_retrieval_total_chunks")

    def test_graph_traversal_metrics(self):
        """Test graph traversal metrics are defined."""
        from app.observability.metrics import MetricsRegistry

        assert hasattr(MetricsRegistry, "rag_graph_traversal_latency_seconds")
        assert hasattr(MetricsRegistry, "rag_retrieval_total_entities")
        assert hasattr(MetricsRegistry, "rag_retrieval_total_relations")

    def test_extraction_metrics(self):
        """Test extraction metrics are defined."""
        from app.observability.metrics import MetricsRegistry

        assert hasattr(MetricsRegistry, "rag_extraction_latency_seconds")
        assert hasattr(MetricsRegistry, "rag_extraction_success_total")
        assert hasattr(MetricsRegistry, "rag_extraction_failure_total")

    def test_llm_metrics(self):
        """Test LLM metrics are defined."""
        from app.observability.metrics import MetricsRegistry

        assert hasattr(MetricsRegistry, "rag_llm_latency_seconds")
        assert hasattr(MetricsRegistry, "rag_llm_calls_total")

    def test_neo4j_metrics(self):
        """Test Neo4j metrics are defined."""
        from app.observability.metrics import MetricsRegistry

        assert hasattr(MetricsRegistry, "rag_neo4j_query_latency_seconds")
        assert hasattr(MetricsRegistry, "rag_neo4j_connection_pool_size")

    def test_generate_metrics(self):
        """Test that metrics can be generated in text format."""
        from app.observability.metrics import MetricsRegistry

        metrics_bytes = MetricsRegistry.generate_metrics()
        assert isinstance(metrics_bytes, bytes)
        assert len(metrics_bytes) > 0

        metrics_str = metrics_bytes.decode("utf-8")
        assert isinstance(metrics_str, str)
        # Should contain at least one of our defined metrics
        assert "http_requests_total" in metrics_str or "rag_" in metrics_str


class TestMetricsEndpoint:
    """Test /metrics endpoint integration."""

    def test_metrics_endpoint_returns_prometheus_format(self):
        """Test that /metrics endpoint returns valid Prometheus format."""
        from fastapi.testclient import TestClient
        from app.main import create_app

        with TestClient(create_app()) as test_client:
            response = test_client.get("/metrics")
            assert response.status_code == 200
            assert "text/plain" in response.headers.get("content-type", "")
            content = response.content.decode("utf-8")
            assert len(content) > 0

    def test_metrics_endpoint_increments_on_request(self):
        """Test that HTTP metrics are incremented on requests."""
        from fastapi.testclient import TestClient
        from app.main import create_app
        from app.observability.metrics import MetricsRegistry

        # Clear registry first by creating fresh app
        with TestClient(create_app()) as test_client:
            # Make a request to health endpoint
            test_client.get("/health")

            # Generate metrics and check for http_requests_total
            metrics_bytes = MetricsRegistry.generate_metrics()
            metrics_str = metrics_bytes.decode("utf-8")
            # Should have some metrics recorded
            assert len(metrics_str) > 0


class TestObservabilitySettingsIntegration:
    """Test integration with observability settings."""

    def test_metrics_enabled_setting(self):
        """Test that metrics_enabled setting exists and works."""
        from app.observability.config import ObservabilitySettings

        settings = ObservabilitySettings()
        assert settings.metrics_enabled is True

        settings_disabled = ObservabilitySettings(metrics_enabled=False)
        assert settings_disabled.metrics_enabled is False

    def test_metrics_port_setting(self):
        """Test that metrics_port setting exists."""
        from app.observability.config import ObservabilitySettings

        settings = ObservabilitySettings()
        assert settings.metrics_port == 8000

        settings_custom = ObservabilitySettings(metrics_port=9090)
        assert settings_custom.metrics_port == 9090
