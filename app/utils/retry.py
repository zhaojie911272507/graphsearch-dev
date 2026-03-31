"""Retry utilities for database operations.

Provides a decorator for automatic retry with exponential backoff.
"""

import asyncio
from functools import wraps
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.config import RetrySettings, get_settings
from app.exceptions import Neo4jConnectionError, Neo4jQueryError


def with_retry(
    max_attempts: int | None = None,
    timeout: float | None = None,
    retry_delay: float | None = None,
    backoff_factor: float | None = None,
):
    """Decorator for retrying database operations with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default: from RetrySettings)
        timeout: Operation timeout in seconds (default: from RetrySettings)
        retry_delay: Initial retry delay in seconds (default: from RetrySettings)
        backoff_factor: Exponential backoff multiplier (default: from RetrySettings)

    Example:
        @with_retry()  # Uses settings from config
        async def get_node_lineage(self, node_id: str) -> dict:
            ...

        @with_retry(max_attempts=5, timeout=60.0)  # Override settings
        async def complex_query(self, node_id: str) -> dict:
            ...
    """
    # Load settings if not provided
    settings = get_settings().retry

    # Use provided values or fall back to settings
    attempts = max_attempts or settings.max_attempts
    op_timeout = timeout or settings.timeout
    min_delay = retry_delay or settings.retry_delay
    multiplier = backoff_factor or settings.backoff_factor

    def decorator(func):
        @wraps(func)
        @retry(
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(multiplier=multiplier, min=min_delay, max=10),
            retry=retry_if_exception_type((Neo4jConnectionError, Neo4jQueryError)),
            reraise=True,
        )
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=op_timeout)
            except asyncio.TimeoutError as exc:
                raise TimeoutError(f"Operation timed out after {op_timeout}s") from exc

        return wrapper

    return decorator
