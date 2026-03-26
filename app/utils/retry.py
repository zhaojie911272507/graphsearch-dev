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

from app.exceptions import Neo4jConnectionError, Neo4jQueryError


def with_retry(max_attempts: int = 3, timeout: float = 30.0):
    """Decorator for retrying database operations with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts (default: 3)
        timeout: Operation timeout in seconds (default: 30.0)

    Example:
        @with_retry(max_attempts=3, timeout=30.0)
        async def get_node_lineage(self, node_id: str) -> dict:
            ...
    """

    def decorator(func):
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((Neo4jConnectionError, Neo4jQueryError)),
            reraise=True,
        )
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            except asyncio.TimeoutError as exc:
                raise TimeoutError(f"Operation timed out after {timeout}s") from exc

        return wrapper

    return decorator
