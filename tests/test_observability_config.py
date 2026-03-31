"""Tests for observability configuration."""

import pytest
from pydantic import ValidationError


class TestObservabilitySettings:
    """Test ObservabilitySettings configuration."""

    def test_default_settings(self):
        """Test that default settings are correctly initialized."""
        from app.observability.config import ObservabilitySettings

        settings = ObservabilitySettings()

        assert settings.otel_enabled is True
        assert settings.otel_exporter_otlp_endpoint == "http://localhost:4318"
        assert settings.otel_traces_sampler == "parentbased_traceidratio"
        assert settings.otel_traces_sampler_arg == 0.1
        assert settings.otel_service_name == "graphrag-api"
        assert settings.otel_resource_attributes == "deployment.environment=development"
        assert settings.metrics_enabled is True
        assert settings.metrics_port == 8000
        assert settings.alertmanager_url == "http://localhost:9093"
        assert settings.webhook_alert_url == ""

    def test_settings_from_env_vars(self, monkeypatch):
        """Test that settings can be overridden via environment variables."""
        from app.observability.config import ObservabilitySettings

        monkeypatch.setenv("OTEL_ENABLED", "false")
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4318")
        monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "0.5")
        monkeypatch.setenv("METRICS_PORT", "9090")

        settings = ObservabilitySettings()

        assert settings.otel_enabled is False
        assert settings.otel_exporter_otlp_endpoint == "http://tempo:4318"
        assert settings.otel_traces_sampler_arg == 0.5
        assert settings.metrics_port == 9090

    def test_traces_sampler_arg_validation(self):
        """Test that traces sampler arg is validated (0.0-1.0)."""
        from app.observability.config import ObservabilitySettings

        # Valid values
        settings = ObservabilitySettings(otel_traces_sampler_arg=0.0)
        assert settings.otel_traces_sampler_arg == 0.0

        settings = ObservabilitySettings(otel_traces_sampler_arg=1.0)
        assert settings.otel_traces_sampler_arg == 1.0

        settings = ObservabilitySettings(otel_traces_sampler_arg=0.5)
        assert settings.otel_traces_sampler_arg == 0.5

    def test_traces_sampler_arg_out_of_range_negative(self):
        """Test that negative traces sampler arg raises validation error."""
        from app.observability.config import ObservabilitySettings

        with pytest.raises(ValidationError):
            ObservabilitySettings(otel_traces_sampler_arg=-0.1)

    def test_traces_sampler_arg_out_of_range_greater_than_one(self):
        """Test that traces sampler arg > 1.0 raises validation error."""
        from app.observability.config import ObservabilitySettings

        with pytest.raises(ValidationError):
            ObservabilitySettings(otel_traces_sampler_arg=1.5)

    def test_factory_function(self):
        """Test the factory function returns correct settings."""
        from app.observability.config import get_observability_settings, ObservabilitySettings

        settings = get_observability_settings()

        assert isinstance(settings, ObservabilitySettings)
        assert settings.otel_service_name == "graphrag-api"
