"""Simulation API routes.

Provides endpoints for:
- Bootstrap simulation (full setup)
- Extract reality seeds
- Generate agent profiles
- Configure simulation worlds
- Query simulation state
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import GraphStoreDep
from app.api.schemas.simulation import (
    AgentGenerateRequest,
    AgentGenerateResponse,
    AgentSchema,
    MemorySchema,
    SeedExtractRequest,
    SeedExtractResponse,
    SimulationBootstrapRequest,
    SimulationBootstrapResponse,
    SimulationParamsSchema,
    SimulationQueryRequest,
    SimulationQueryResponse,
    SimulationSessionSchema,
    WorldConfigRequest,
    WorldConfigResponse,
)
from app.config import get_settings
from app.services.environment_config import SimulationParameters
from app.services.profile_generator import ProfileGeneratorAgent
from app.services.seed_extractor import SeedExtractorAgent
from app.services.simulation_orchestrator import (
    SimulationBootstrapConfig,
    SimulationOrchestrator,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simulation", tags=["Social Simulation"])


def _agent_node_to_schema(agent_node, memories=None) -> AgentSchema:
    """Convert AgentNode to AgentSchema."""
    from app.domain.social.nodes import AgentNode

    profile_dict = agent_node.profile.model_dump() if hasattr(agent_node.profile, "model_dump") else agent_node.profile
    personality_dict = agent_node.personality.model_dump() if hasattr(agent_node.personality, "model_dump") else agent_node.personality

    return AgentSchema(
        id=agent_node.id,
        name=agent_node.name,
        platform=agent_node.platform.value,
        state=agent_node.state.value,
        profile=profile_dict,
        personality=personality_dict,
        background_story=agent_node.background_story,
        goals=agent_node.goals,
        memory_count=len(agent_node.memory_ids) if hasattr(agent_node, "memory_ids") else 0,
        created_at=agent_node.metadata.created_at,
    )


@router.post(
    "/bootstrap",
    response_model=SimulationBootstrapResponse,
    summary="Bootstrap simulation",
    description="Initialize a complete simulation with seeds, agents, and worlds.",
)
async def bootstrap_simulation(
    request: SimulationBootstrapRequest,
    store: GraphStoreDep,
) -> SimulationBootstrapResponse:
    """Bootstrap a complete simulation.

    This endpoint:
    1. Extracts reality seeds from provided sources
    2. Generates agent profiles
    3. Configures simulation worlds
    4. Persists everything to the graph store
    """
    try:
        settings = get_settings()

        # Build simulation parameters
        sim_params = SimulationParameters(
            max_agents=request.parameters.max_agents,
            memory_decay_rate=request.parameters.memory_decay_rate,
            interaction_probability=request.parameters.interaction_probability,
            platform_sync_interval=request.parameters.platform_sync_interval,
            simulation_speed=request.parameters.simulation_speed,
            enable_emotion=request.parameters.enable_emotion,
            enable_memory_formation=request.parameters.enable_memory_formation,
            enable_relationship_evolution=request.parameters.enable_relationship_evolution,
        )

        # Build bootstrap config
        config = SimulationBootstrapConfig(
            name=request.name,
            description=request.description,
            seed_sources=request.seed_sources,
            agent_count=request.agent_count,
            platforms=request.platforms,
            parameters=sim_params,
        )

        # Create orchestrator and bootstrap
        orchestrator = SimulationOrchestrator(
            openai_settings=settings.openai,
            graph_store=store,
        )

        result = await orchestrator.bootstrap(config)

        # Build response
        session_schema = SimulationSessionSchema(
            id=result.session.id,
            session_id=result.session.session_id,
            name=result.session.name,
            status=result.session.status.value,
            start_time=result.session.start_time,
            end_time=result.session.end_time,
            agent_count=len(result.agents),
            world_count=len(result.worlds),
            parameters=result.session.parameters,
        )

        return SimulationBootstrapResponse(
            session=session_schema,
            agents_created=len(result.agents),
            worlds_created=len(result.worlds),
            seeds_processed=len(result.seeds),
            status="success",
            message=f"Simulation '{request.name}' bootstrapped with {len(result.agents)} agents across {len(result.worlds)} worlds",
        )

    except Exception as e:
        logger.exception("Bootstrap simulation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bootstrap failed: {e}",
        ) from e


@router.post(
    "/seeds/extract",
    response_model=SeedExtractResponse,
    summary="Extract reality seed",
    description="Extract entities and relationships from a reality seed.",
)
async def extract_seed(
    request: SeedExtractRequest,
    store: GraphStoreDep,
) -> SeedExtractResponse:
    """Extract entities and relationships from a reality seed."""
    try:
        settings = get_settings()

        extractor = SeedExtractorAgent(settings.openai)
        result = await extractor.extract_seed(
            source_url=request.source_url,
            source_type=request.source_type,
            raw_content=request.raw_content,
            metadata=request.metadata,
        )

        # Persist seed
        await store.merge_nodes([result.seed_node])

        return SeedExtractResponse(
            seed_id=result.seed_node.id,
            source_url=result.seed_node.source_url,
            source_type=result.seed_node.source_type.value,
            extracted_at=result.seed_node.extracted_at,
            credibility_score=result.seed_node.credibility_score,
            extracted_entity_count=result.statistics.get("entity_count", 0),
            extracted_agent_count=result.statistics.get("potential_agent_count", 0),
            status="success",
        )

    except Exception as e:
        logger.exception("Seed extraction failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Seed extraction failed: {e}",
        ) from e


@router.post(
    "/agents/generate",
    response_model=AgentGenerateResponse,
    summary="Generate agents",
    description="Generate agent profiles from seed data.",
)
async def generate_agents(
    request: AgentGenerateRequest,
    store: GraphStoreDep,
) -> AgentGenerateResponse:
    """Generate agent profiles from seed data."""
    try:
        settings = get_settings()

        # Fetch seeds if provided
        seeds_data = []
        if request.seed_ids:
            # In a real implementation, fetch from graph store
            logger.info("Would fetch seeds: %s", request.seed_ids)

        generator = ProfileGeneratorAgent(settings.openai)

        # Use a placeholder seed if none provided
        if not request.seed_ids:
            seed_data = {
                "title": "Default Simulation",
                "raw_content": "Generate diverse characters for a social simulation.",
            }
        else:
            seed_data = {"title": "User Provided", "raw_content": ""}

        from app.domain.social.enums import PlatformType
        platform = PlatformType(request.platform) if request.platform in [p.value for p in PlatformType] else PlatformType.WECHAT

        result = await generator.generate_profiles(
            seed_data=seed_data,
            profile_count=request.profile_count,
            platform=platform,
        )

        # Persist agents
        for agent in result.agents:
            await store.merge_nodes([agent])
        for memory in result.memories:
            await store.merge_nodes([memory])
        if result.relationships:
            await store.merge_relationships(result.relationships)

        agents_schema = [
            _agent_node_to_schema(agent) for agent in result.agents
        ]

        return AgentGenerateResponse(
            agents=agents_schema,
            seed_ids=request.seed_ids,
            generation_timestamp=datetime.utcnow(),
            status="success",
        )

    except Exception as e:
        logger.exception("Agent generation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent generation failed: {e}",
        ) from e


@router.post(
    "/world/configure",
    response_model=WorldConfigResponse,
    summary="Configure simulation world",
    description="Configure a simulation world with platform settings.",
)
async def configure_world(
    request: WorldConfigRequest,
    store: GraphStoreDep,
) -> WorldConfigResponse:
    """Configure a simulation world."""
    try:
        settings = get_settings()

        config_agent = SimulationParameters()  # Use defaults

        from app.domain.social.enums import PlatformType
        platform = PlatformType(request.platform) if request.platform in [p.value for p in PlatformType] else PlatformType.WECHAT

        env_config = type("EnvConfig", (), {
            "configure_world": lambda self, **kwargs: type("WorldResult", (), {
                "world_state": type("WorldState", (), {
                    "id": UUID(int=1),
                    "name": request.name,
                    "world_key": request.world_key,
                    "platform": platform,
                    "timestamp": datetime.utcnow(),
                })(),
                "platform_config": None,
            })()
        })()

        result = env_config.configure_world(
            world_key=request.world_key,
            name=request.name,
            description=request.description,
            platform=platform,
            state_data=request.state_data,
            platform_config=request.platform_config,
        )

        # Persist world state
        await store.merge_nodes([result.world_state])

        return WorldConfigResponse(
            world_id=result.world_state.id,
            world_key=result.world_state.world_key,
            name=result.world_state.name,
            platform=result.world_state.platform.value,
            timestamp=result.world_state.timestamp,
            status="success",
        )

    except Exception as e:
        logger.exception("World configuration failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"World configuration failed: {e}",
        ) from e


@router.get(
    "/sessions/{session_id}",
    summary="Get simulation session",
    description="Get details of a simulation session.",
)
async def get_simulation_session(
    session_id: UUID,
    store: GraphStoreDep,
):
    """Get simulation session details."""
    try:
        # Query from graph store
        # This is a placeholder - actual implementation would query Neo4j
        return {
            "session_id": str(session_id),
            "status": "running",
            "agent_count": 0,
            "world_count": 0,
        }
    except Exception as e:
        logger.exception("Failed to get session: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session: {e}",
        ) from e


@router.post(
    "/sessions/{session_id}/start",
    summary="Start simulation",
    description="Start or resume a simulation session.",
)
async def start_simulation(
    session_id: UUID,
    store: GraphStoreDep,
):
    """Start or resume a simulation session."""
    try:
        # Update session status to RUNNING
        # This is a placeholder - actual implementation would update Neo4j
        return {
            "session_id": str(session_id),
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.exception("Failed to start session: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start session: {e}",
        ) from e


@router.post(
    "/query",
    response_model=SimulationQueryResponse,
    summary="Query simulation state",
    description="Query various aspects of simulation state.",
)
async def query_simulation(
    request: SimulationQueryRequest,
    store: GraphStoreDep,
) -> SimulationQueryResponse:
    """Query simulation state."""
    try:
        data = []
        count = 0

        # Query based on type
        if request.query_type == "STATUS":
            data = {"status": "running", "timestamp": datetime.utcnow().isoformat()}
            count = 1
        elif request.query_type == "AGENTS":
            # Query agents from graph
            data = []
            count = 0
        elif request.query_type == "MEMORIES":
            data = []
            count = 0
        elif request.query_type == "WORLDS":
            data = []
            count = 0

        return SimulationQueryResponse(
            data=data,
            count=count,
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        logger.exception("Query failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {e}",
        ) from e
