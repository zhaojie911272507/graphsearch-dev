"""Audit logging service.

Tracks system changes and user actions for compliance and debugging.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.domain.audit import AuditEvent, AuditAction
from app.config import Settings
from app.persistence.graph_store import GraphStore

logger = logging.getLogger(__name__)


class AuditLogger:
    """Audit logging service."""

    def __init__(self, graph_store: GraphStore, settings: Settings):
        self.graph_store = graph_store
        self.enabled = settings.app.audit_enabled if hasattr(settings.app, "audit_enabled") else True

    async def log_event(
        self,
        action: AuditAction,
        user_id: str,
        resource_type: str,
        resource_id: str,
        changes: Optional[dict] = None,
        ip_address: Optional[str] = None,
    ) -> AuditEvent:
        """Log an audit event to Neo4j.

        Args:
            action: The type of action performed
            user_id: ID of the user performing the action
            resource_type: Type of resource (entity_type, relation_type, pipeline, etc.)
            resource_id: ID of the affected resource
            changes: Optional dictionary of changes made
            ip_address: Optional IP address of the request

        Returns:
            AuditEvent object
        """
        if not self.enabled:
            return None

        from uuid import uuid4

        event = AuditEvent(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
            ip_address=ip_address,
        )

        try:
            await self._save_to_neo4j(event)
            logger.info(f"Audit event logged: {action.value} by {user_id} on {resource_type}:{resource_id}")
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}", exc_info=True)

        return event

    async def _save_to_neo4j(self, event: AuditEvent):
        """Save audit event to Neo4j."""
        query = """
        CREATE (e:AuditEvent {
            id: $id,
            timestamp: $timestamp,
            user_id: $user_id,
            action: $action,
            resource_type: $resource_type,
            resource_id: $resource_id,
            changes: $changes,
            ip_address: $ip_address
        })
        RETURN e
        """

        params = {
            "id": str(event.id),
            "timestamp": event.timestamp.isoformat(),
            "user_id": event.user_id,
            "action": event.action.value,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "changes": event.changes,
            "ip_address": event.ip_address,
        }

        async with self.graph_store.driver.session() as session:
            await session.run(query, params)

    async def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """Query audit logs.

        Args:
            user_id: Filter by user ID
            action: Filter by action type
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            limit: Maximum number of results

        Returns:
            List of AuditEvent objects
        """
        query = """
        MATCH (e:AuditEvent)
        WHERE ($user_id IS NULL OR e.user_id = $user_id)
          AND ($action IS NULL OR e.action = $action)
          AND ($resource_type IS NULL OR e.resource_type = $resource_type)
          AND ($resource_id IS NULL OR e.resource_id = $resource_id)
        RETURN e
        ORDER BY e.timestamp DESC
        LIMIT $limit
        """

        params = {
            "user_id": user_id,
            "action": action.value if action else None,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "limit": limit,
        }

        async with self.graph_store.driver.session() as session:
            result = await session.run(query, params)
            records = await result.data()

            events = []
            for record in records:
                e = record["e"]
                events.append(AuditEvent(
                    id=e["id"],
                    timestamp=datetime.fromisoformat(e["timestamp"]),
                    user_id=e["user_id"],
                    action=AuditAction(e["action"]),
                    resource_type=e["resource_type"],
                    resource_id=e["resource_id"],
                    changes=e.get("changes"),
                    ip_address=e.get("ip_address"),
                ))

            return events
