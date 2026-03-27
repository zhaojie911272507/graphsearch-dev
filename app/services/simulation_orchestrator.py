"""Simulation Orchestrator.

Orchestrates the full simulation bootstrap process:
1. Extract reality seeds
2. Generate agent profiles
3. Configure simulation world
4. Persist all nodes to graph store
5. Initialize simulation session
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.config import OpenAISettings
from app.domain.relationships import GraphRelationship
from app.domain.social.enums import PlatformType, SimulationStatus
from app.domain.social.relationships import SocialRelationType
from app.domain.social.nodes import (
    AgentNode,
    MemoryNode,
    SeedNode,
    SimulationSessionNode,
    WorldStateNode,
)
from app.services.environment_config import (
    EnvironmentConfigAgent,
    PlatformConfig,
    SimulationParameters,
)
from app.services.profile_generator import ProfileGeneratorAgent, ProfileGenerationResult
from app.services.seed_extractor import SeedExtractorAgent, SeedExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class SimulationBootstrapConfig:
    """Configuration for bootstrapping a simulation."""

    name: str
    description: str = ""
    seed_sources: list[dict] = field(default_factory=list)
    agent_count: int = 10
    platforms: list[str] = field(default_factory=lambda: ["WECHAT"])
    parameters: SimulationParameters = field(default_factory=SimulationParameters)
    custom_platform_configs: dict[str, dict] = field(default_factory=dict)


@dataclass
class BootstrapProgress:
    """Progress tracking for bootstrap process."""

    stage: str = "INITIALIZING"
    seeds_processed: int = 0
    agents_generated: int = 0
    worlds_created: int = 0
    total_steps: int = 5
    current_step: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class SimulationBootstrapResult:
    """Result of full simulation bootstrap."""

    session: SimulationSessionNode
    seeds: list[SeedNode]
    agents: list[AgentNode]
    memories: list[MemoryNode]
    worlds: list[WorldStateNode]
    agent_relationships: list[GraphRelationship]
    platform_configs: dict[PlatformType, PlatformConfig]
    parameters: SimulationParameters
    statistics: dict = field(default_factory=dict)


class SimulationOrchestrator:
    """Orchestrator for the full simulation bootstrap process.

    This class coordinates:
    1. SeedExtractorAgent for reality seed processing
    2. ProfileGeneratorAgent for agent creation
    3. EnvironmentConfigAgent for world setup
    4. GraphStore for persistence

    Usage:
        orchestrator = SimulationOrchestrator(openai_settings, graph_store)
        result = await orchestrator.bootstrap(config)
    """

    def __init__(
        self,
        openai_settings: OpenAISettings,
        graph_store: "GraphStore",  # type: ignore
    ) -> None:
        self._openai_settings = openai_settings
        self._graph_store = graph_store

        # Initialize agents
        self._seed_extractor = SeedExtractorAgent(openai_settings)
        self._profile_generator = ProfileGeneratorAgent(openai_settings)
        self._environment_config = EnvironmentConfigAgent(openai_settings)

        # Progress tracking
        self._progress = BootstrapProgress()

    @property
    def progress(self) -> BootstrapProgress:
        """Get current bootstrap progress."""
        return self._progress

    async def bootstrap(self, config: SimulationBootstrapConfig) -> SimulationBootstrapResult:
        """Bootstrap a complete simulation.

        Args:
            config: Bootstrap configuration

        Returns:
            SimulationBootstrapResult with all created entities

        Process:
        1. Extract reality seeds
        2. Generate agent profiles from seeds
        3. Configure simulation worlds
        4. Create all nodes in graph store
        5. Link entities together
        6. Initialize session
        """
        self._progress = BootstrapProgress(total_steps=5)
        errors = []

        # Stage 1: Extract reality seeds
        self._progress.stage = "EXTRACTING_SEEDS"
        self._progress.current_step = 1
        seeds_result = await self._extract_seeds(config.seed_sources)
        if seeds_result.errors:
            errors.extend(seeds_result.errors)

        # Stage 2: Generate agent profiles
        self._progress.stage = "GENERATING_AGENTS"
        self._progress.current_step = 2
        agents_result = await self._generate_agents(
            seeds_result.seed_nodes,
            config.agent_count,
            config.platforms,
        )
        if agents_result.errors:
            errors.extend(agents_result.errors)

        # Stage 3: Configure worlds
        self._progress.stage = "CONFIGURING_WORLDS"
        self._progress.current_step = 3
        worlds_result = await self._configure_worlds(
            config.name,
            config.description,
            config.platforms,
            config.custom_platform_configs,
        )
        if worlds_result.errors:
            errors.extend(worlds_result.errors)

        # Stage 4: Persist to graph store
        self._progress.stage = "PERSISTING_TO_GRAPH"
        self._progress.current_step = 4
        await self._persist_all(
            seeds_result.seed_nodes,
            agents_result.agents,
            agents_result.memories,
            worlds_result.world_states,
            agents_result.relationships,
        )

        # Stage 5: Create and finalize session
        self._progress.stage = "FINALIZING_SESSION"
        self._progress.current_step = 5
        session = await self._create_session(
            config.name,
            config.description,
            seeds_result.seed_nodes,
            agents_result.agents,
            worlds_result.world_states,
            config.parameters,
        )

        # Update progress
        self._progress.seeds_processed = len(seeds_result.seed_nodes)
        self._progress.agents_generated = len(agents_result.agents)
        self._progress.worlds_created = len(worlds_result.world_states)

        # Build result
        return SimulationBootstrapResult(
            session=session,
            seeds=seeds_result.seed_nodes,
            agents=agents_result.agents,
            memories=agents_result.memories,
            worlds=worlds_result.world_states,
            agent_relationships=agents_result.relationships,
            platform_configs=worlds_result.platform_configs,
            parameters=config.parameters,
            statistics={
                "seed_count": len(seeds_result.seed_nodes),
                "agent_count": len(agents_result.agents),
                "memory_count": len(agents_result.memories),
                "world_count": len(worlds_result.world_states),
                "relationship_count": len(agents_result.relationships),
                "errors": errors,
            },
        )

    async def _extract_seeds(
        self, seed_sources: list[dict]
    ) -> dataclass:
        """Extract entities from reality seeds."""
        seed_nodes = []
        errors = []

        for i, source in enumerate(seed_sources):
            try:
                source_type = source.get("source_type", "TEXT")
                source_url = source.get("url")
                raw_content = source.get("content", "")
                metadata = source.get("metadata", {})

                result = await self._seed_extractor.extract_seed(
                    source_url=source_url,
                    source_type=source_type,
                    raw_content=raw_content,
                    metadata=metadata,
                )
                seed_nodes.append(result.seed_node)

            except Exception as e:
                error_msg = f"Failed to extract seed {i}: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)

        return type("SeedResult", (), {"seed_nodes": seed_nodes, "errors": errors})()

    async def _generate_agents(
        self,
        seed_nodes: list[SeedNode],
        agent_count: int,
        platforms: list[str],
    ) -> dataclass:
        """Generate agent profiles from seeds."""
        all_agents = []
        all_memories = []
        all_relationships = []
        errors = []

        # Distribute agent count across platforms
        agents_per_platform = max(1, agent_count // len(platforms)) if platforms else agent_count

        for platform_str in platforms:
            platform = PlatformType(platform_str)

            # Generate profiles for this platform
            for seed in seed_nodes:
                try:
                    seed_data = {
                        "title": seed.title,
                        "raw_content": seed.raw_content[:2000],
                    }

                    result = await self._profile_generator.generate_profiles(
                        seed_data=seed_data,
                        profile_count=agents_per_platform,
                        platform=platform,
                    )

                    # Link agents to seeds
                    for agent in result.agents:
                        agent_memory = agent.model_copy(
                            update={"seed_id": seed.id}
                        )
                        all_agents.append(agent_memory)

                    all_memories.extend(result.memories)
                    all_relationships.extend(result.relationships)

                except Exception as e:
                    error_msg = f"Failed to generate agents from seed {seed.id}: {e}"
                    logger.warning(error_msg)
                    errors.append(error_msg)

        # Limit to requested count
        all_agents = all_agents[:agent_count]

        return type("AgentsResult", (), {
            "agents": all_agents,
            "memories": all_memories,
            "relationships": all_relationships,
            "errors": errors,
        })()

    async def _configure_worlds(
        self,
        name: str,
        description: str,
        platforms: list[str],
        custom_configs: dict[str, dict],
    ) -> dataclass:
        """Configure simulation worlds for each platform."""
        world_states = []
        platform_configs = {}
        errors = []

        for platform_str in platforms:
            try:
                custom_config = custom_configs.get(platform_str)
                platform_config = self._environment_config.setup_platform_config(
                    platform_str, custom_config
                )

                world_result = self._environment_config.configure_world(
                    world_key=f"{name.lower()}_{platform_str.lower()}",
                    name=f"{name} - {platform_str}",
                    description=description,
                    platform=PlatformType(platform_str),
                    platform_config=platform_config,
                )

                world_states.append(world_result.world_state)
                platform_configs[world_result.world_state.platform] = world_result.platform_config

            except Exception as e:
                error_msg = f"Failed to configure world for {platform_str}: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)

        return type("WorldsResult", (), {
            "world_states": world_states,
            "platform_configs": platform_configs,
            "errors": errors,
        })()

    async def _persist_all(
        self,
        seed_nodes: list[SeedNode],
        agent_nodes: list[AgentNode],
        memory_nodes: list[MemoryNode],
        world_nodes: list[WorldStateNode],
        relationships: list[GraphRelationship],
    ) -> None:
        """Persist all nodes and relationships to graph store."""
        try:
            # Persist seeds
            for seed in seed_nodes:
                await self._graph_store.merge_nodes([seed])

            # Persist agents
            for agent in agent_nodes:
                await self._graph_store.merge_nodes([agent])

            # Persist memories
            for memory in memory_nodes:
                await self._graph_store.merge_nodes([memory])

            # Persist worlds
            for world in world_nodes:
                await self._graph_store.merge_nodes([world])

            # Persist relationships
            if relationships:
                await self._graph_store.merge_relationships(relationships)

            # Create agent-memory links
            for agent in agent_nodes:
                for memory_id in agent.memory_ids:
                    rel = GraphRelationship(
                        relation_type=SocialRelationType.HAS_MEMORY,
                        source_id=agent.id,
                        target_id=memory_id,
                        weight=1.0,
                    )
                    await self._graph_store.merge_relationships([rel])

            logger.info(
                "Persisted: %d seeds, %d agents, %d memories, %d worlds, %d relationships",
                len(seed_nodes),
                len(agent_nodes),
                len(memory_nodes),
                len(world_nodes),
                len(relationships),
            )

        except Exception as e:
            logger.error("Failed to persist to graph store: %s", e)
            raise

    async def _create_session(
        self,
        name: str,
        description: str,
        seeds: list[SeedNode],
        agents: list[AgentNode],
        worlds: list[WorldStateNode],
        parameters: SimulationParameters,
    ) -> SimulationSessionNode:
        """Create and finalize simulation session."""
        session = SimulationSessionNode(
            name=name,
            definition=description,
            status=SimulationStatus.INITIALIZING,
            parameters=parameters.__dict__,
            seed_ids=[s.id for s in seeds],
            agent_ids=[a.id for a in agents],
            world_ids=[w.id for w in worlds],
            start_time=datetime.utcnow(),
        )

        # Persist session
        await self._graph_store.merge_nodes([session])

        # Create session relationships
        session_rels = []
        for agent_id in session.agent_ids:
            session_rels.append(
                GraphRelationship(
                    relation_type=SocialRelationType.PART_OF_SESSION,
                    source_id=agent_id,
                    target_id=session.id,
                    weight=1.0,
                )
            )
        for world_id in session.world_ids:
            session_rels.append(
                GraphRelationship(
                    relation_type=SocialRelationType.WORLD_OF_SESSION,
                    source_id=world_id,
                    target_id=session.id,
                    weight=1.0,
                )
            )

        if session_rels:
            await self._graph_store.merge_relationships(session_rels)

        return session
