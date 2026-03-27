"""Simulation Report API routes.

Provides endpoints for:
- Generating simulation reports
- Getting agent analysis
- Querying past reports
"""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import GraphStoreDep
from app.api.schemas.simulation import ReportType
from app.config import get_settings
from app.services.report_generation import ReportAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulation/reports", tags=["Simulation Reports"])


@router.post(
    "/generate",
    response_model=dict,
    summary="Generate simulation report",
    description="Generate a comprehensive analysis report for a simulation.",
)
async def generate_report(
    session_id: UUID,
    store: GraphStoreDep,
    report_type: str = Query(default="DAILY_SUMMARY"),
    days_back: int = Query(default=1, ge=1, le=30),
) -> dict:
    """Generate a simulation report."""
    try:
        settings = get_settings()

        report_agent = ReportAgent(
            openai_settings=settings.openai,
            graph_store=store,
        )

        # Parse report type
        try:
            rtype = ReportType(report_type)
        except ValueError:
            rtype = ReportType.DAILY_SUMMARY

        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days_back)

        # Generate report
        report = await report_agent.generate_simulation_report(
            session_id=session_id,
            report_type=rtype,
            time_range=(start_time, end_time),
        )

        return {
            "report_id": str(report.session_id),  # Use session_id as report_id for now
            "report_type": report.report_type.value,
            "generated_at": report.generated_at.isoformat(),
            "time_range": {
                "start": report.time_range[0].isoformat(),
                "end": report.time_range[1].isoformat(),
            },
            "summary": report.executive_summary,
            "statistics": {
                "total_agents": report.total_agents,
                "total_interactions": report.total_interactions,
                "total_memories": report.total_memories,
            },
            "recommendations": report.recommendations,
        }

    except Exception as e:
        logger.exception("Failed to generate report: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {e}",
        ) from e


@router.get(
    "/{report_id}",
    summary="Get report",
    description="Get a specific report by ID.",
)
async def get_report(
    report_id: UUID,
    store: GraphStoreDep,
) -> dict:
    """Get a specific report."""
    try:
        # In real implementation, query from graph store
        return {
            "report_id": str(report_id),
            "status": "not_found",
            "message": "Report retrieval not yet implemented",
        }

    except Exception as e:
        logger.exception("Failed to get report: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get report: {e}",
        ) from e


@router.get(
    "/session/{session_id}",
    summary="Get session reports",
    description="Get all reports for a simulation session.",
)
async def get_session_reports(
    session_id: UUID,
    store: GraphStoreDep,
    limit: int = Query(default=10, ge=1, le=100),
) -> dict:
    """Get all reports for a session."""
    try:
        # In real implementation, query from graph store
        return {
            "session_id": str(session_id),
            "reports": [],
            "total": 0,
            "limit": limit,
        }

    except Exception as e:
        logger.exception("Failed to get session reports: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session reports: {e}",
        ) from e


@router.get(
    "/agents/{agent_id}/analysis",
    summary="Get agent analysis",
    description="Get behavioral analysis for a specific agent.",
)
async def get_agent_analysis(
    agent_id: UUID,
    store: GraphStoreDep,
) -> dict:
    """Get agent analysis report."""
    try:
        settings = get_settings()

        report_agent = ReportAgent(
            openai_settings=settings.openai,
            graph_store=store,
        )

        report = await report_agent.generate_agent_analysis(agent_id=agent_id)

        return {
            "agent_id": str(report.agent_id),
            "agent_name": report.agent_name,
            "generated_at": report.generated_at.isoformat(),
            "statistics": {
                "total_posts": report.total_posts,
                "total_interactions": report.total_interactions,
                "followers": report.followers,
                "following": report.following,
            },
            "behavioral_summary": report.behavioral_summary,
            "personality_expression": report.personality_expression,
        }

    except Exception as e:
        logger.exception("Failed to get agent analysis: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent analysis: {e}",
        ) from e


@router.get(
    "/world/{world_id}/state",
    summary="Get world state report",
    description="Get the current state report for a simulation world.",
)
async def get_world_state(
    world_id: UUID,
    store: GraphStoreDep,
) -> dict:
    """Get world state report."""
    try:
        settings = get_settings()

        report_agent = ReportAgent(
            openai_settings=settings.openai,
            graph_store=store,
        )

        report = await report_agent.generate_world_state_report(world_id=world_id)

        return report

    except Exception as e:
        logger.exception("Failed to get world state: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get world state: {e}",
        ) from e


@router.get(
    "/session/{session_id}/network",
    summary="Get network analysis",
    description="Get social network analysis for a simulation session.",
)
async def get_network_analysis(
    session_id: UUID,
    store: GraphStoreDep,
) -> dict:
    """Get network analysis for a session."""
    try:
        settings = get_settings()

        report_agent = ReportAgent(
            openai_settings=settings.openai,
            graph_store=store,
        )

        metrics = await report_agent.generate_network_analysis(session_id=session_id)

        return {
            "session_id": str(session_id),
            "metrics": {
                "total_nodes": metrics.total_nodes,
                "total_edges": metrics.total_edges,
                "average_degree": metrics.average_degree,
                "clustering_coefficient": metrics.clustering_coefficient,
                "connected_components": metrics.connected_components,
                "central_agents": metrics.central_agents,
            },
        }

    except Exception as e:
        logger.exception("Failed to get network analysis: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get network analysis: {e}",
        ) from e
