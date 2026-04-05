"""Observability configuration via pydantic-settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ObservabilitySettings(BaseSettings):
    """Observability configuration for monitoring and tracing."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    # OpenTelemetry
    otel_enabled: bool = Field(default=True, description="Enable OpenTelemetry tracing")
    otel_exporter_otlp_endpoint: str = Field(
        default="http://tempo:4318",
        description="OTLP HTTP endpoint for Tempo",
    )
    otel_traces_sampler: str = Field(
        default="parentbased_traceidratio",
        description="Trace sampler type",
    )
    otel_traces_sampler_arg: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Trace sampling rate (0.0-1.0)",
    )
    otel_service_name: str = Field(default="graphrag-api", description="Service name for traces")
    otel_resource_attributes: str = Field(
        default="deployment.environment=development",
        description="Additional resource attributes",
    )

    # Metrics
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=8000, description="Port for metrics endpoint")

    # Alerting
    alertmanager_url: str = Field(default="http://localhost:9093", description="Alertmanager URL")
    webhook_alert_url: str = Field(default="", description="Webhook URL for alert notifications")

    # Query performance monitoring
    slow_query_threshold_ms: float = Field(default=1000.0, ge=100, description="Threshold in ms for slow query logging")
    log_slow_queries: bool = Field(default=True, description="Enable slow query logging")


def get_observability_settings() -> ObservabilitySettings:
    """Factory function for observability settings."""
    return ObservabilitySettings()