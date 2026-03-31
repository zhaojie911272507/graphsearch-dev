"""Audit log API routes.

Provides endpoints for:
- Querying audit logs
- Filtering by user, action, resource type
"""
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import GraphStoreDep
from app.domain.audit import AuditAction, AuditEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["Audit Logging"])


@router.get("/logs", summary="List audit logs")
async def list_audit_logs(
    store: GraphStoreDep,
    user_id: str | None = Query(default=None, description="Filter by user ID"),
    action: str | None = Query(default=None, description="Filter by action type"),
    resource_type: str | None = Query(default=None, description="Filter by resource type"),
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[dict]:
    """List audit logs with optional filters."""
    try:
        from app.persistence.audit_log import AuditLogger

        audit_logger = AuditLogger(store, store._settings)

        action_enum = None
        if action:
            try:
                action_enum = AuditAction(action)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid action type: {action}",
                )

        logs = await audit_logger.get_audit_logs(
            user_id=user_id,
            action=action_enum,
            resource_type=resource_type,
            limit=limit,
        )

        return [log.model_dump() for log in logs]
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to list audit logs: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list audit logs: {exc}",
        ) from exc


@router.get("/logs/{log_id}", summary="Get audit log by ID")
async def get_audit_log(
    log_id: str,
    store: GraphStoreDep,
) -> dict:
    """Get a specific audit log by ID."""
    try:
        from app.persistence.audit_log import AuditLogger

        audit_logger = AuditLogger(store, store._settings)

        # Query the database directly for a single log
        query = """
        MATCH (e:AuditEvent {id: $log_id})
        RETURN e
        """

        async with store.driver.session(database=store._settings.database) as session:
            result = await session.run(query, log_id=log_id)
            record = await result.single()

            if not record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Audit log {log_id} not found",
                )

            e = record["e"]
            event = AuditEvent(
                id=e["id"],
                timestamp=datetime.fromisoformat(e["timestamp"]),
                user_id=e["user_id"],
                action=AuditAction(e["action"]),
                resource_type=e["resource_type"],
                resource_id=e["resource_id"],
                changes=e.get("changes"),
                ip_address=e.get("ip_address"),
            )

            return event.model_dump()
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get audit log: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit log: {exc}",
        ) from exc
