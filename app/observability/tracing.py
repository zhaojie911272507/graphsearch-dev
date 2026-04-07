"""OpenTelemetry distributed tracing setup."""

import logging
from typing import TYPE_CHECKING, Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


class TracingSetup:
    """Manages OpenTelemetry tracing lifecycle."""

    _tracer_provider: TracerProvider | None = None
    _tracer: trace.Tracer | None = None

    @classmethod
    def initialize(cls, settings: "Settings") -> None:
        """Initialize OpenTelemetry tracing."""
        if not settings.observability.otel_enabled:
            logger.info("OpenTelemetry tracing disabled")
            return

        resource_attributes: dict[str, str] = {
            SERVICE_NAME: settings.observability.otel_service_name,
            "service.version": "0.1.0",
        }

        extra_attrs = settings.observability.otel_resource_attributes
        if extra_attrs:
            for attr in extra_attrs.split(","):
                if "=" in attr:
                    key, value = attr.split("=", 1)
                    resource_attributes[key.strip()] = value.strip()

        resource = Resource.create(resource_attributes)

        sampler = ParentBasedTraceIdRatio(
            float(settings.observability.otel_traces_sampler_arg)
        )

        cls._tracer_provider = TracerProvider(
            resource=resource,
            sampler=sampler,
        )

        exporter = OTLPSpanExporter(
            endpoint=settings.observability.otel_exporter_otlp_endpoint + "/v1/traces",
            timeout=5,
        )

        span_processor = BatchSpanProcessor(exporter)
        cls._tracer_provider.add_span_processor(span_processor)

        trace.set_tracer_provider(cls._tracer_provider)

        cls._tracer = cls._tracer_provider.get_tracer(
            settings.observability.otel_service_name
        )

        logger.info(
            "OpenTelemetry tracing initialized",
            extra={
                "endpoint": settings.observability.otel_exporter_otlp_endpoint,
                "service_name": settings.observability.otel_service_name,
                "sampling_rate": settings.observability.otel_traces_sampler_arg,
            },
        )

    @classmethod
    def get_tracer(cls, name: str | None = None) -> trace.Tracer:
        """Get a tracer instance."""
        if cls._tracer is None:
            return trace.get_tracer(name or "graphrag")
        return cls._tracer

    @classmethod
    def instrument_app(cls, app: Any) -> None:
        """Instrument FastAPI application."""
        if not cls._tracer_provider:
            logger.warning("Cannot instrument app: tracing not initialized")
            return

        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=cls._tracer_provider,
        )

        HTTPXClientInstrumentor().instrument(tracer_provider=cls._tracer_provider)

        AsyncioInstrumentor().instrument(tracer_provider=cls._tracer_provider)

        logger.info("Application instrumentation complete")

    @classmethod
    def shutdown(cls) -> None:
        """Clean up tracing resources."""
        if cls._tracer_provider:
            cls._tracer_provider.shutdown()
            cls._tracer_provider = None
            cls._tracer = None
            logger.info("OpenTelemetry tracing shutdown complete")
