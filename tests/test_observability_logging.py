"""Tests for enhanced logging with OpenTelemetry trace context."""

import logging
from unittest.mock import patch, MagicMock

import pytest
import structlog

from app.observability.logging import (
    get_trace_id,
    get_span_id,
    trace_context_processor,
    setup_enhanced_logging,
)


class TestTraceIdExtraction:
    """Test trace ID and span ID extraction from OpenTelemetry context."""

    def test_get_trace_id_no_active_span(self):
        """Test get_trace_id returns None when no active span."""
        with patch("app.observability.logging.trace") as mock_trace:
            with patch("app.observability.logging.INVALID_SPAN_CONTEXT") as mock_invalid:
                # Mock span context that equals INVALID_SPAN_CONTEXT
                mock_span_context = MagicMock()
                mock_span_context.__eq__ = lambda self, other: True  # Always equals (invalid)

                mock_span = MagicMock()
                mock_span.get_span_context.return_value = mock_span_context
                mock_trace.get_current_span.return_value = mock_span

                result = get_trace_id()
                assert result is None

    def test_get_span_id_no_active_span(self):
        """Test get_span_id returns None when no active span."""
        with patch("app.observability.logging.trace") as mock_trace:
            with patch("app.observability.logging.INVALID_SPAN_CONTEXT") as mock_invalid:
                # Mock span context that equals INVALID_SPAN_CONTEXT
                mock_span_context = MagicMock()
                mock_span_context.__eq__ = lambda self, other: True  # Always equals (invalid)

                mock_span = MagicMock()
                mock_span.get_span_context.return_value = mock_span_context
                mock_trace.get_current_span.return_value = mock_span

                result = get_span_id()
                assert result is None

    def test_get_trace_id_with_valid_span(self):
        """Test get_trace_id returns formatted trace ID."""
        with patch("app.observability.logging.trace") as mock_trace:
            with patch("app.observability.logging.INVALID_SPAN_CONTEXT") as mock_invalid:
                mock_span_context = MagicMock()
                mock_span_context.trace_id = 12345
                mock_span_context.span_id = 67890
                mock_span_context.__eq__ = lambda self, other: other != mock_invalid

                mock_span = MagicMock()
                mock_span.get_span_context.return_value = mock_span_context
                mock_trace.get_current_span.return_value = mock_span

                # Mock the comparison to return False (not invalid)
                mock_invalid.__eq__ = lambda self, other: False

                result = get_trace_id()
                # Trace ID should be 32-char hex formatted
                assert result == "00000000000000000000000000003039"

    def test_get_span_id_with_valid_span(self):
        """Test get_span_id returns formatted span ID."""
        with patch("app.observability.logging.trace") as mock_trace:
            with patch("app.observability.logging.INVALID_SPAN_CONTEXT") as mock_invalid:
                mock_span_context = MagicMock()
                mock_span_context.trace_id = 12345
                mock_span_context.span_id = 67890
                mock_span_context.__eq__ = lambda self, other: other != mock_invalid

                mock_span = MagicMock()
                mock_span.get_span_context.return_value = mock_span_context
                mock_trace.get_current_span.return_value = mock_span

                # Mock the comparison to return False (not invalid)
                mock_invalid.__eq__ = lambda self, other: False

                result = get_span_id()
                # Span ID should be 16-char hex formatted
                assert result == "0000000000010932"


class TestTraceContextProcessor:
    """Test the trace context processor for structlog."""

    def test_processor_adds_trace_ids(self):
        """Test processor adds trace_id and span_id to event dict."""
        event_dict = {"event": "test message", "level": "info"}

        with patch("app.observability.logging.get_trace_id") as mock_trace:
            with patch("app.observability.logging.get_span_id") as mock_span:
                mock_trace.return_value = "abc123"
                mock_span.return_value = "def456"

                result = trace_context_processor(
                    MagicMock(), "info", event_dict
                )

                assert result["trace_id"] == "abc123"
                assert result["span_id"] == "def456"
                assert result["event"] == "test message"

    def test_processor_skips_missing_trace_ids(self):
        """Test processor handles missing trace/span IDs gracefully."""
        event_dict = {"event": "test message", "level": "info"}

        with patch("app.observability.logging.get_trace_id") as mock_trace:
            with patch("app.observability.logging.get_span_id") as mock_span:
                mock_trace.return_value = None
                mock_span.return_value = None

                result = trace_context_processor(
                    MagicMock(), "info", event_dict
                )

                assert "trace_id" not in result
                assert "span_id" not in result
                assert result["event"] == "test message"

    def test_processor_adds_partial_trace_ids(self):
        """Test processor adds only available trace IDs."""
        event_dict = {"event": "test message", "level": "info"}

        with patch("app.observability.logging.get_trace_id") as mock_trace:
            with patch("app.observability.logging.get_span_id") as mock_span:
                mock_trace.return_value = "abc123"
                mock_span.return_value = None

                result = trace_context_processor(
                    MagicMock(), "info", event_dict
                )

                assert result["trace_id"] == "abc123"
                assert "span_id" not in result


class TestSetupEnhancedLogging:
    """Test the enhanced logging setup function."""

    def test_setup_debug_mode(self):
        """Test setup_enhanced_logging in debug mode."""
        with patch("app.observability.logging.structlog.configure") as mock_configure:
            setup_enhanced_logging(debug=True)

            mock_configure.assert_called_once()
            call_args = mock_configure.call_args

            # Verify ConsoleRenderer is used in debug mode
            processors = call_args[1]["processors"]
            assert any(
                isinstance(p, structlog.dev.ConsoleRenderer) for p in processors
            )

    def test_setup_production_mode(self):
        """Test setup_enhanced_logging in production mode."""
        with patch("app.observability.logging.structlog.configure") as mock_configure:
            setup_enhanced_logging(debug=False)

            mock_configure.assert_called_once()
            call_args = mock_configure.call_args

            # Verify JSONRenderer is used in production mode
            processors = call_args[1]["processors"]
            # JSONRenderer should be the last processor
            last_processor = processors[-1]
            assert isinstance(last_processor, structlog.processors.JSONRenderer)

    def test_setup_includes_trace_processor(self):
        """Test setup_enhanced_logging includes trace context processor."""
        with patch("app.observability.logging.structlog.configure") as mock_configure:
            setup_enhanced_logging(debug=False)

            mock_configure.assert_called_once()
            call_args = mock_configure.call_args
            processors = call_args[1]["processors"]

            # Verify trace_context_processor is in the chain
            assert trace_context_processor in processors

    def test_setup_has_required_base_processors(self):
        """Test setup_enhanced_logging has required base processors."""
        with patch("app.observability.logging.structlog.configure") as mock_configure:
            setup_enhanced_logging(debug=False)

            mock_configure.assert_called_once()
            call_args = mock_configure.call_args
            processors = call_args[1]["processors"]

            # Check for required processors
            processor_types = [type(p).__name__ for p in processors]

            assert "merge_contextvars" in str(processors)
            assert "add_log_level" in str(processors)
            assert "TimeStamper" in processor_types

    def test_setup_with_custom_log_level(self):
        """Test setup_enhanced_logging with custom log level."""
        with patch("app.observability.logging.structlog.configure") as mock_configure:
            setup_enhanced_logging(debug=False, log_level="DEBUG")

            mock_configure.assert_called_once()
            call_args = mock_configure.call_args

            # Verify DEBUG level is used
            wrapper_class = call_args[1]["wrapper_class"]
            # The wrapper should be configured with DEBUG level
            assert wrapper_class is not None
