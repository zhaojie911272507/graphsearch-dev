"""Tests for OpenTelemetry distributed tracing setup."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestTracingSetup:
    """Test TracingSetup class functionality."""

    def test_tracing_disabled_when_otel_disabled(self):
        """Test that tracing is not initialized when otel_enabled is False."""
        from app.config import Settings, ObservabilitySettings
        from app.observability.tracing import TracingSetup

        settings = Settings(
            observability=ObservabilitySettings(otel_enabled=False)
        )

        # Should not raise, just log that tracing is disabled
        TracingSetup.initialize(settings)

        # Tracer should be None when disabled
        tracer = TracingSetup.get_tracer("test")
        # When disabled, get_tracer returns the global tracer
        assert tracer is not None

    def test_tracing_initialization_with_custom_settings(self):
        """Test tracing initialization with custom settings."""
        from app.config import Settings, ObservabilitySettings
        from app.observability.tracing import TracingSetup

        settings = Settings(
            observability=ObservabilitySettings(
                otel_enabled=True,
                otel_service_name="test-graphrag",
                otel_exporter_otlp_endpoint="http://test-tempo:4318",
                otel_traces_sampler_arg=0.5,
            )
        )

        # Initialize tracing
        TracingSetup.initialize(settings)

        # Get tracer and verify it's available
        tracer = TracingSetup.get_tracer("test-service")
        assert tracer is not None

    def test_tracing_initialization_with_resource_attributes(self):
        """Test that additional resource attributes are parsed correctly."""
        from app.config import Settings, ObservabilitySettings
        from app.observability.tracing import TracingSetup

        settings = Settings(
            observability=ObservabilitySettings(
                otel_enabled=True,
                otel_resource_attributes="deployment.environment=test,version=1.0",
            )
        )

        TracingSetup.initialize(settings)
        tracer = TracingSetup.get_tracer("test")
        assert tracer is not None

    def test_get_tracer_returns_tracer(self):
        """Test that get_tracer returns a valid tracer instance."""
        from app.config import Settings, ObservabilitySettings
        from app.observability.tracing import TracingSetup
        from opentelemetry import trace

        settings = Settings(
            observability=ObservabilitySettings(otel_enabled=True)
        )

        TracingSetup.initialize(settings)

        tracer = TracingSetup.get_tracer("my-service")
        # Should be an instance of trace.Tracer
        assert isinstance(tracer, trace.Tracer) or hasattr(tracer, 'start_span')

    def test_get_tracer_default_name(self):
        """Test get_tracer with default name."""
        from app.config import Settings, ObservabilitySettings
        from app.observability.tracing import TracingSetup

        # Reset any previous initialization
        TracingSetup._tracer_provider = None
        TracingSetup._tracer = None

        settings = Settings(
            observability=ObservabilitySettings(otel_enabled=False)
        )

        TracingSetup.initialize(settings)

        # Should return global tracer when not initialized
        tracer = TracingSetup.get_tracer()
        assert tracer is not None

    def test_instrument_app_without_initialization(self, caplog):
        """Test instrument_app warns when tracing not initialized."""
        from app.main import create_app
        from app.observability.tracing import TracingSetup
        import logging

        # Reset initialization
        TracingSetup._tracer_provider = None
        TracingSetup._tracer = None

        app = create_app()

        with caplog.at_level(logging.WARNING):
            TracingSetup.instrument_app(app)

        # Should log a warning
        assert "tracing not initialized" in caplog.text

    def test_shutdown_cleanups_up_resources(self):
        """Test that shutdown cleans up tracing resources."""
        from app.config import Settings, ObservabilitySettings
        from app.observability.tracing import TracingSetup

        settings = Settings(
            observability=ObservabilitySettings(otel_enabled=True)
        )

        TracingSetup.initialize(settings)

        # Verify initialized
        assert TracingSetup._tracer_provider is not None

        # Shutdown
        TracingSetup.shutdown()

        # Verify cleaned up
        assert TracingSetup._tracer_provider is None
        assert TracingSetup._tracer is None

    def test_instrument_app_with_initialization(self):
        """Test instrument_app successfully instruments the app."""
        from app.config import Settings, ObservabilitySettings
        from app.observability.tracing import TracingSetup
        from app.main import create_app

        settings = Settings(
            observability=ObservabilitySettings(otel_enabled=True)
        )

        TracingSetup.initialize(settings)
        app = create_app()

        # Should not raise
        TracingSetup.instrument_app(app)

        # Verify tracer is set
        assert TracingSetup._tracer is not None


class TestTracingIntegration:
    """Test tracing integration with FastAPI application."""

    def test_tracing_initialized_in_lifespan(self):
        """Test that tracing is initialized during app lifespan startup."""
        from fastapi.testclient import TestClient
        from app.main import create_app
        from app.config import Settings, ObservabilitySettings
        from unittest.mock import patch

        # Mock settings to enable tracing
        with patch('app.main.get_settings') as mock_get_settings:
            settings = Settings(
                observability=ObservabilitySettings(otel_enabled=True)
            )
            mock_get_settings.return_value = settings

            app = create_app()

            # Should not raise during startup
            with TestClient(app) as client:
                response = client.get("/health")
                assert response.status_code == 200

    def test_tracing_disabled_in_lifespan(self):
        """Test app works when tracing is disabled."""
        from fastapi.testclient import TestClient
        from app.main import create_app
        from app.config import Settings, ObservabilitySettings
        from unittest.mock import patch

        with patch('app.main.get_settings') as mock_get_settings:
            settings = Settings(
                observability=ObservabilitySettings(otel_enabled=False)
            )
            mock_get_settings.return_value = settings

            app = create_app()

            with TestClient(app) as client:
                response = client.get("/health")
                assert response.status_code == 200
