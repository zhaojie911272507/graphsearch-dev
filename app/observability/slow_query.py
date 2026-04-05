"""Slow query logging utilities."""

import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)


def log_slow_query(
    operation: str,
    threshold_ms: float | None = None,
) -> Callable:
    """Decorator to log slow queries.

    Args:
        operation: Name of the operation being timed
        threshold_ms: Custom threshold in ms (uses config default if None)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Import here to avoid circular import
            from app.config import get_settings
            settings = get_settings()
            threshold = threshold_ms or settings.observability.slow_query_threshold_ms

            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start) * 1000

                if settings.observability.log_slow_queries and elapsed_ms > threshold:
                    logger.warning(
                        "Slow query detected",
                        extra={
                            "operation": operation,
                            "elapsed_ms": round(elapsed_ms, 2),
                            "threshold_ms": threshold,
                        },
                    )
                return result
            except Exception:
                elapsed_ms = (time.perf_counter() - start) * 1000
                if elapsed_ms > threshold:
                    logger.error(
                        "Slow query failed",
                        extra={
                            "operation": operation,
                            "elapsed_ms": round(elapsed_ms, 2),
                            "threshold_ms": threshold,
                            "status": "error",
                        },
                    )
                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Import here to avoid circular import
            from app.config import get_settings
            settings = get_settings()
            threshold = threshold_ms or settings.observability.slow_query_threshold_ms

            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start) * 1000

                if settings.observability.log_slow_queries and elapsed_ms > threshold:
                    logger.warning(
                        "Slow query detected",
                        extra={
                            "operation": operation,
                            "elapsed_ms": round(elapsed_ms, 2),
                            "threshold_ms": threshold,
                        },
                    )
                return result
            except Exception:
                elapsed_ms = (time.perf_counter() - start) * 1000
                if elapsed_ms > threshold:
                    logger.error(
                        "Slow query failed",
                        extra={
                            "operation": operation,
                            "elapsed_ms": round(elapsed_ms, 2),
                            "threshold_ms": threshold,
                            "status": "error",
                        },
                    )
                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator

