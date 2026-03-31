"""Enhanced logging with OpenTelemetry trace context."""

import logging
from typing import Any

import structlog
from opentelemetry import trace
from opentelemetry.trace import SpanContext, INVALID_SPAN_CONTEXT


def get_trace_id() -> str | None:
    """Get current trace ID from OpenTelemetry context."""
    current_span = trace.get_current_span()
    span_context = current_span.get_span_context()

    if span_context == INVALID_SPAN_CONTEXT:
        return None

    return format(span_context.trace_id, "032x")


def get_span_id() -> str | None:
    """Get current span ID from OpenTelemetry context."""
    current_span = trace.get_current_span()
    span_context = current_span.get_span_context()

    if span_context == INVALID_SPAN_CONTEXT:
        return None

    return format(span_context.span_id, "016x")


def trace_context_processor(
    logger: logging.Logger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Add trace_id and span_id to log events."""
    trace_id = get_trace_id()
    span_id = get_span_id()

    if trace_id:
        event_dict["trace_id"] = trace_id
    if span_id:
        event_dict["span_id"] = span_id

    return event_dict


def setup_enhanced_logging(debug: bool = False, log_level: str = "INFO") -> None:
    """Configure structlog with trace context propagation."""
    level = getattr(logging, log_level.upper(), logging.INFO)

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        trace_context_processor,  # Add trace context
    ]

    if debug:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
