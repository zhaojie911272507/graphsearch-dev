"""Simulation Execution API routes.

Provides endpoints for:
- Starting/pausing/stopping simulations
- Running simulation steps
- Querying simulation status and metrics
- Listing and creating simulation sessions
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import GraphStoreDep
from app.config import get_settings
from app.domain.social.enums import PlatformType, SimulationStatus
from app.services.environment_config import (
    DEFAULT_WECHAT_CONFIG,
    DEFAULT_XIAOHONGSHU_CONFIG,
    SimulationParameters,
)
from app.services.simulation_execution import SimulationEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulation", tags=["Simulation Execution"])


@router.get(
    "/sessions",
    summary="List simulation sessions",
    description="List all simulation sessions with optional status filtering.",
)
async def list_simulation_sessions(
    store: GraphStoreDep,
    status_filter: str | None = Query(default=None, description="Filter by status"),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    """List simulation sessions."""
    try:
        # Query sessions from graph store
        sessions = await store.get_simulation_sessions(
            status_filter=status_filter,
            limit=limit,
        )

        return {
            "sessions": sessions,
            "total": len(sessions),
            "limit": limit,
        }

    except Exception as e:
        logger.exception("Failed to list simulation sessions: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list simulation sessions: {e}",
        ) from e


@router.post(
    "/sessions",
    summary="Create simulation session",
    description="Create a new simulation session.",
)
async def create_simulation_session(
    store: GraphStoreDep,
    session_data: dict,
) -> dict:
    """Create a simulation session."""
    try:
        import uuid

        session_id = str(uuid.uuid4())

        # Create simulation session node in graph
        session_info = {
            "id": session_id,
            "name": session_data.get("name", "Unnamed Simulation"),
            "status": "INITIALIZING",
            "agent_count": session_data.get("agent_count", 10),
            "platforms": session_data.get("platforms", []),
            "created_at": datetime.utcnow().isoformat(),
            "current_step": 0,
            "total_steps": session_data.get("total_steps", 100),
        }

        # In real implementation, create SimulationSessionNode in graph store
        # await store.create_simulation_session(session_info)

        return {
            "session_id": session_id,
            "status": "created",
            "session": session_info,
        }

    except Exception as e:
        logger.exception("Failed to create simulation session: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create simulation session: {e}",
        ) from e


@router.get(
    "/sessions/{session_id}",
    summary="Get simulation session",
    description="Get details of a simulation session.",
)
async def get_simulation_session(
    session_id: UUID,
    store: GraphStoreDep,
) -> dict:
    """Get a simulation session."""
    try:
        # Query from graph store
        session = await store.get_simulation_session_by_id(str(session_id))

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get simulation session: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get simulation session: {e}",
        ) from e


@router.delete(
    "/sessions/{session_id}",
    summary="Delete simulation session",
    description="Delete a simulation session.",
)
async def delete_simulation_session(
    session_id: UUID,
    store: GraphStoreDep,
) -> dict:
    """Delete a simulation session."""
    try:
        # Delete from graph store
        await store.delete_simulation_session(str(session_id))

        return {
            "session_id": str(session_id),
            "status": "deleted",
        }

    except Exception as e:
        logger.exception("Failed to delete simulation session: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete simulation session: {e}",
        ) from e


@router.post(
    "/sessions/{session_id}/start",
    summary="Start simulation",
    description="Start or resume a simulation session.",
)
async def start_simulation(
    session_id: UUID,
    store: GraphStoreDep,
) -> dict:
    """Start a simulation session."""
    try:
        settings = get_settings()

        engine = SimulationEngine(
            openai_settings=settings.openai,
            graph_store=store,
        )

        success = await engine.start_simulation(session_id)

        # Update session status in graph
        # In real implementation, update the SimulationSessionNode

        return {
            "session_id": str(session_id),
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "message": "Simulation started successfully",
        }

    except Exception as e:
        logger.exception("Failed to start simulation: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start simulation: {e}",
        ) from e


@router.post(
    "/sessions/{session_id}/pause",
    summary="Pause simulation",
    description="Pause a running simulation session.",
)
async def pause_simulation(
    session_id: UUID,
    store: GraphStoreDep,
) -> dict:
    """Pause a simulation session."""
    try:
        settings = get_settings()

        engine = SimulationEngine(
            openai_settings=settings.openai,
            graph_store=store,
        )

        success = await engine.pause_simulation(session_id)

        return {
            "session_id": str(session_id),
            "status": "paused",
            "paused_at": datetime.utcnow().isoformat(),
            "message": "Simulation paused successfully",
        }

    except Exception as e:
        logger.exception("Failed to pause simulation: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause simulation: {e}",
        ) from e


@router.post(
    "/sessions/{session_id}/stop",
    summary="Stop simulation",
    description="Stop a simulation session completely.",
)
async def stop_simulation(
    session_id: UUID,
    store: GraphStoreDep,
) -> dict:
    """Stop a simulation session."""
    try:
        settings = get_settings()

        engine = SimulationEngine(
            openai_settings=settings.openai,
            graph_store=store,
        )

        success = await engine.stop_simulation(session_id)

        return {
            "session_id": str(session_id),
            "status": "stopped",
            "stopped_at": datetime.utcnow().isoformat(),
            "message": "Simulation stopped successfully",
        }

    except Exception as e:
        logger.exception("Failed to stop simulation: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop simulation: {e}",
        ) from e


@router.post(
    "/sessions/{session_id}/step",
    summary="Run simulation step",
    description="Run a single simulation step.",
)
async def run_simulation_step(
    session_id: UUID,
    store: GraphStoreDep,
    step_count: int = 1,
) -> dict:
    """Run one or more simulation steps."""
    try:
        settings = get_settings()

        engine = SimulationEngine(
            openai_settings=settings.openai,
            graph_store=store,
        )

        # In real implementation, fetch agents and worlds from graph
        # For now, return mock result
        results = []
        for i in range(step_count):
            step_result = {
                "step_number": i + 1,
                "timestamp": datetime.utcnow().isoformat(),
                "interactions_generated": 0,
                "memories_created": 0,
            }
            results.append(step_result)

        return {
            "session_id": str(session_id),
            "steps_run": len(results),
            "results": results,
        }

    except Exception as e:
        logger.exception("Failed to run simulation step: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run simulation step: {e}",
        ) from e


@router.get(
    "/sessions/{session_id}/status",
    summary="Get simulation status",
    description="Get the current status of a simulation session.",
)
async def get_simulation_status(
    session_id: UUID,
    store: GraphStoreDep,
) -> dict:
    """Get simulation status."""
    try:
        # In real implementation, query from graph store
        return {
            "session_id": str(session_id),
            "status": "running",
            "current_step": 0,
            "started_at": datetime.utcnow().isoformat(),
            "last_step_at": None,
            "metrics": {
                "total_agents": 0,
                "total_interactions": 0,
                "total_memories": 0,
            },
        }

    except Exception as e:
        logger.exception("Failed to get simulation status: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get simulation status: {e}",
        ) from e


@router.get(
    "/sessions/{session_id}/metrics",
    summary="Get simulation metrics",
    description="Get detailed metrics for a simulation session.",
)
async def get_simulation_metrics(
    session_id: UUID,
    store: GraphStoreDep,
) -> dict:
    """Get simulation metrics."""
    try:
        # In real implementation, calculate from graph data
        return {
            "session_id": str(session_id),
            "timestamp": datetime.utcnow().isoformat(),
            "overview": {
                "total_agents": 0,
                "active_agents": 0,
                "total_interactions": 0,
                "total_memories": 0,
            },
            "platform_breakdown": {
                "WECHAT": {
                    "agents": 0,
                    "posts": 0,
                    "interactions": 0,
                },
                "XIAOHONGSHU": {
                    "agents": 0,
                    "posts": 0,
                    "interactions": 0,
                },
            },
            "temporal": {
                "peak_activity_hour": 12,
                "average_interactions_per_step": 0.0,
            },
        }

    except Exception as e:
        logger.exception("Failed to get simulation metrics: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get simulation metrics: {e}",
        ) from e


@router.get(
    "/sessions/{session_id}/agents",
    summary="Get simulation agents",
    description="Get all agents in a simulation session.",
)
async def get_simulation_agents(
    session_id: UUID,
    store: GraphStoreDep,
    limit: int = 100,
) -> dict:
    """Get agents in a simulation."""
    try:
        # In real implementation, query from graph store
        return {
            "session_id": str(session_id),
            "agents": [],
            "total": 0,
            "limit": limit,
        }

    except Exception as e:
        logger.exception("Failed to get simulation agents: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get simulation agents: {e}",
        ) from e


@router.post(
    "/sessions/{session_id}/memory/decay",
    summary="Apply memory decay",
    description="Apply memory decay to all agent memories.",
)
async def apply_memory_decay(
    session_id: UUID,
    store: GraphStoreDep,
    decay_rate: float = 0.1,
) -> dict:
    """Apply memory decay to agent memories."""
    try:
        from app.services.simulation_execution import MemoryManager

        memory_manager = MemoryManager(store)

        # In real implementation, apply to all agents in session
        result = await memory_manager.update_temporal_memories(
            session_id=session_id,
            timestamp=datetime.utcnow(),
        )

        return {
            "session_id": str(session_id),
            "decay_rate": decay_rate,
            "applied_at": datetime.utcnow().isoformat(),
            "result": result,
        }

    except Exception as e:
        logger.exception("Failed to apply memory decay: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply memory decay: {e}",
        ) from e
