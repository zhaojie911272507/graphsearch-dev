"""Webhook service for async notifications."""

import hashlib
import hmac
import json
import logging
from typing import Any

import httpx

from app.config import WebhookSettings

logger = logging.getLogger(__name__)


class WebhookError(Exception):
    """Webhook related errors."""

    pass


class WebhookService:
    """Service for sending webhook notifications."""

    def __init__(self, settings: WebhookSettings | None = None) -> None:
        self._settings = settings or WebhookSettings()

    def _generate_signature(self, payload: str) -> str:
        """Generate HMAC signature for payload."""
        if not self._settings.secret:
            return ""
        return hmac.new(
            self._settings.secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

    async def send(
        self,
        event: str,
        data: dict[str, Any],
    ) -> bool:
        """Send webhook notification.

        Args:
            event: Event type (e.g., 'ingestion.completed', 'evaluation.completed')
            data: Event payload

        Returns:
            True if webhook was sent successfully
        """
        if not self._settings.enabled or not self._settings.url:
            logger.debug("Webhook disabled or URL not configured")
            return False

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": event,
        }

        # Add signature if secret is configured
        payload_str = json.dumps(data, sort_keys=True)
        signature = self._generate_signature(payload_str)
        if signature:
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        async with httpx.AsyncClient(timeout=self._settings.timeout) as client:
            try:
                response = await client.post(
                    self._settings.url,
                    json=data,
                    headers=headers,
                )
                response.raise_for_status()
                logger.info("Webhook sent successfully", extra={"event": event})
                return True
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "Webhook failed with status %d: %s",
                    exc.response.status_code,
                    exc.response.text[:500],
                )
                return False
            except Exception as exc:
                logger.error("Webhook failed: %s", exc)
                return False
