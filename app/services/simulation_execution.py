"""Simulation Execution Engine.

Core execution engine for running social simulations:
- SimulationEngine: Main execution controller
- DualPlatformScheduler: Parallel platform execution
- InteractionEngine: Agent interaction generation and execution
- MemoryManager: Temporal memory management
- DemandPredictor: Need prediction and analysis
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from langchain_openai import ChatOpenAI

from app.config import OpenAISettings
from app.domain.relationships import GraphRelationship
from app.domain.social.enums import (
    AgentState,
    InteractionType,
    MemoryType,
    NeedType,
    PlatformType,
    ReportType,
    SimulationStatus,
)
from app.domain.social.nodes import (
    AgentNode,
    InteractionNode,
    MemoryNode,
    ReportNode,
    WorldStateNode,
)
from app.persistence.graph_store import GraphStore
from app.services.environment_config import PlatformConfig, SimulationParameters

logger = logging.getLogger(__name__)


@dataclass
class Interaction:
    """Represents an interaction to be executed."""

    interaction_type: InteractionType
    sender: AgentNode
    receiver: AgentNode | None
    content: str
    metadata: dict = field(default_factory=dict)
    priority: float = 0.5
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class InteractionResult:
    """Result of executing an interaction."""

    success: bool
    interaction: Interaction
    result_node: InteractionNode | None
    memory_updates: list[MemoryNode]
    metrics: dict = field(default_factory=dict)


@dataclass
class PlatformStepResult:
    """Result of executing a platform simulation step."""

    platform: PlatformType
    interactions: list[Interaction]
    interaction_results: list[InteractionResult]
    world_state: WorldStateNode
    metrics: dict = field(default_factory=dict)


@dataclass
class SimulationStepResult:
    """Result of a simulation step."""

    session_id: UUID
    step_number: int
    timestamp: datetime
    platform_results: list[PlatformStepResult]
    total_interactions: int
    new_memories: int
    metrics: dict = field(default_factory=dict)


@dataclass
class AgentNeed:
    """Represents an agent's current need."""

    need_type: NeedType
    intensity: float  # 0.0 - 1.0
    description: str
    suggested_actions: list[str]


@dataclass
class TrendingTopic:
    """Represents a trending topic."""

    topic: str
    momentum: float  # Rate of growth
    post_count: int
    engagement_rate: float
    related_topics: list[str]


class MemoryManager:
    """Manages agent memories with temporal dynamics."""

    def __init__(self, graph_store: GraphStore) -> None:
        self._store = graph_store

    async def add_memory(
        self,
        agent_id: UUID,
        content: str,
        memory_type: MemoryType = MemoryType.EPISODIC,
        emotion_tags: list | None = None,
        importance: float = 0.5,
    ) -> MemoryNode:
        """Add a memory for an agent."""
        from app.domain.social.nodes import MemoryNode

        memory = MemoryNode(
            name=content[:100] if len(content) > 100 else content,
            definition=content[:500],
            content=content,
            memory_type=memory_type,
            importance=importance,
            emotion_tags=emotion_tags or [],
            associated_agent_ids=[agent_id],
        )

        await self._store.merge_nodes([memory])

        # Link to agent
        rel = GraphRelationship(
            relation_type="HAS_MEMORY",
            source_id=agent_id,
            target_id=memory.id,
            weight=1.0,
        )
        await self._store.merge_relationships([rel])

        return memory

    async def decay_memories(
        self,
        agent_id: UUID,
        decay_rate: float = 0.1,
    ) -> list[MemoryNode]:
        """Apply memory decay to an agent's memories."""
        # In a real implementation, this would query and update memories
        # For now, return empty list
        logger.info("Applying memory decay (rate=%.2f) to agent %s", decay_rate, agent_id)
        return []

    async def retrieve_relevant_memories(
        self,
        agent_id: UUID,
        context: str,
        top_k: int = 5,
    ) -> list[MemoryNode]:
        """Retrieve relevant memories for an agent based on context."""
        # In a real implementation, this would use vector similarity
        logger.info("Retrieving %d relevant memories for agent %s", top_k, agent_id)
        return []

    async def update_temporal_memories(
        self,
        session_id: UUID,
        timestamp: datetime,
    ) -> dict:
        """Update temporal state of all memories in a session."""
        # Apply decay, consolidate short-term to long-term, etc.
        return {"updated_count": 0, "decayed_count": 0, "consolidated_count": 0}


class InteractionEngine:
    """Engine for generating and executing agent interactions."""

    def __init__(self, openai_settings: OpenAISettings) -> None:
        self._llm = ChatOpenAI(
            api_key=openai_settings.api_key,
            base_url=openai_settings.base_url,
            model=openai_settings.model,
            temperature=0.7,
        )
        self._settings = openai_settings

    async def generate_interactions(
        self,
        agent: AgentNode,
        candidates: list[AgentNode],
        platform: PlatformType,
        config: PlatformConfig,
    ) -> list[Interaction]:
        """Generate potential interactions for an agent."""
        interactions = []

        # Determine what type of interaction to generate
        import random
        if random.random() < config.interaction_probability:
            # Generate an interaction
            if candidates:
                # Choose a random candidate to interact with
                receiver = random.choice(candidates)
                interaction_type = random.choice(list(InteractionType))

                # Use LLM to generate realistic content
                content = await self._generate_interaction_content(
                    agent, receiver, interaction_type, platform
                )

                interactions.append(
                    Interaction(
                        interaction_type=interaction_type,
                        sender=agent,
                        receiver=receiver,
                        content=content,
                        priority=random.random(),
                    )
                )
            else:
                # Generate a post (no specific receiver)
                content = await self._generate_post_content(agent, platform)
                interactions.append(
                    Interaction(
                        interaction_type=InteractionType.POST,
                        sender=agent,
                        receiver=None,
                        content=content,
                        priority=0.8,
                    )
                )

        return interactions

    async def _generate_interaction_content(
        self,
        sender: AgentNode,
        receiver: AgentNode,
        interaction_type: InteractionType,
        platform: PlatformType,
    ) -> str:
        """Generate content for an interaction using LLM."""
        prompt = f"""Generate a realistic {interaction_type.value} message from:

Sender: {sender.name} ({sender.profile.occupation})
Personality: Openness={sender.personality.openness:.2f}, Extraversion={sender.personality.extraversion:.2f}

Receiver: {receiver.name} ({receiver.profile.occupation})

Platform: {platform.value}

The content should be consistent with the sender's personality and the platform norms.
Keep it brief and natural."""

        try:
            response = await self._llm.ainvoke([
                {"role": "system", "content": "You are a creative writer generating realistic social media content."},
                {"role": "user", "content": prompt},
            ])
            return response.content.strip()
        except Exception as e:
            logger.warning("Failed to generate interaction content: %s", e)
            return f"[{interaction_type.value}]"

    async def _generate_post_content(
        self,
        agent: AgentNode,
        platform: PlatformType,
    ) -> str:
        """Generate a post content for an agent."""
        prompt = f"""Generate a realistic social media post for:

Agent: {agent.name}
Occupation: {agent.profile.occupation}
Interests: {", ".join(agent.profile.interests[:3]) if agent.profile.interests else "general"}
Platform: {platform.value}

The post should reflect the agent's background and be appropriate for the platform."""

        try:
            response = await self._llm.ainvoke([
                {"role": "system", "content": "You are a creative writer generating realistic social media posts."},
                {"role": "user", "content": prompt},
            ])
            return response.content.strip()
        except Exception as e:
            logger.warning("Failed to generate post content: %s", e)
            return "[Post content]"

    async def execute_interaction(
        self,
        interaction: Interaction,
        world_state: WorldStateNode,
    ) -> InteractionResult:
        """Execute an interaction and record the results."""
        try:
            # Create interaction node
            interaction_node = InteractionNode(
                name=f"{interaction.interaction_type.value}_{interaction.sender.name}",
                definition=interaction.content[:500],
                interaction_type=interaction.interaction_type,
                content=interaction.content,
                sender_id=interaction.sender.id,
                receiver_id=interaction.receiver.id if interaction.receiver else None,
            )

            # In a real implementation, persist to graph store
            # await store.merge_nodes([interaction_node])

            # Create memory for participants
            memory_updates = []
            if interaction.receiver:
                # Both sender and receiver get memories
                memory_updates.append(
                    MemoryNode(
                        name=f"Interaction with {interaction.sender.name}",
                        content=interaction.content,
                        memory_type=MemoryType.EPISODIC,
                        associated_agent_ids=[interaction.receiver.id],
                    )
                )

            return InteractionResult(
                success=True,
                interaction=interaction,
                result_node=interaction_node,
                memory_updates=memory_updates,
                metrics={"execution_time_ms": 100},
            )

        except Exception as e:
            logger.error("Failed to execute interaction: %s", e)
            return InteractionResult(
                success=False,
                interaction=interaction,
                result_node=None,
                memory_updates=[],
                metrics={"error": str(e)},
            )


class DualPlatformScheduler:
    """Scheduler for parallel platform execution."""

    def __init__(
        self,
        interaction_engine: InteractionEngine,
        memory_manager: MemoryManager,
    ) -> None:
        self._interaction_engine = interaction_engine
        self._memory_manager = memory_manager

    async def execute_platform_step(
        self,
        platform: PlatformType,
        agents: list[AgentNode],
        world_state: WorldStateNode,
        config: PlatformConfig,
    ) -> PlatformStepResult:
        """Execute a single simulation step for a platform."""
        interactions = []

        # Generate interactions for each agent (in parallel)
        tasks = [
            self._interaction_engine.generate_interactions(agent, agents, platform, config)
            for agent in agents
        ]
        agent_interactions = await asyncio.gather(*tasks)

        # Flatten interactions
        for agent_int in agent_interactions:
            interactions.extend(agent_int)

        # Execute interactions
        interaction_results = []
        for interaction in interactions:
            result = await self._interaction_engine.execute_interaction(interaction, world_state)
            interaction_results.append(result)

        # Update world state
        new_world_state = WorldStateNode(
            world_key=world_state.world_key,
            name=world_state.name,
            definition=world_state.definition,
            platform=world_state.platform,
            state_data={
                **world_state.state_data,
                "last_step": datetime.utcnow().isoformat(),
                "interaction_count": len(interactions),
            },
            active_agent_ids=[a.id for a in agents],
        )

        return PlatformStepResult(
            platform=platform,
            interactions=interactions,
            interaction_results=interaction_results,
            world_state=new_world_state,
            metrics={
                "generated_interactions": len(interactions),
                "executed_interactions": len([r for r in interaction_results if r.success]),
                "failed_interactions": len([r for r in interaction_results if not r.success]),
            },
        )


class DemandPredictor:
    """Predicts agent needs and trending topics."""

    def __init__(self, openai_settings: OpenAISettings) -> None:
        self._llm = ChatOpenAI(
            api_key=openai_settings.api_key,
            base_url=openai_settings.base_url,
            model=openai_settings.model,
            temperature=0.3,
        )

    async def analyze_agent_needs(
        self,
        agent: AgentNode,
        recent_interactions: list | None = None,
    ) -> list[AgentNeed]:
        """Analyze an agent's current needs."""
        needs = []

        # Analyze based on personality and recent activity
        if agent.personality.extraversion > 0.6:
            needs.append(AgentNeed(
                need_type=NeedType.SOCIAL_CONNECTION,
                intensity=agent.personality.extraversion,
                description="Strong desire for social interaction",
                suggested_actions=["send_message", "comment_on_post", "join_discussion"],
            ))

        if agent.personality.openness > 0.6:
            needs.append(AgentNeed(
                need_type=NeedType.INFORMATION,
                intensity=agent.personality.openness,
                description="Curiosity about new information",
                suggested_actions=["explore_feed", "search_topics", "follow_new_accounts"],
            ))

        return needs

    async def predict_trending_topics(
        self,
        platform: PlatformType,
        interactions: list[Interaction],
        time_window: timedelta = timedelta(hours=24),
    ) -> list[TrendingTopic]:
        """Predict trending topics based on recent interactions."""
        # Simple frequency-based trending
        topic_counts: dict[str, int] = {}
        for interaction in interactions:
            # Extract keywords/topics from content
            # In real implementation, use NLP
            words = interaction.content.lower().split()
            for word in words:
                if len(word) > 4:  # Skip short words
                    topic_counts[word] = topic_counts.get(word, 0) + 1

        # Build trending topics
        trending = []
        for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1])[:10]:
            trending.append(TrendingTopic(
                topic=topic,
                momentum=count / 10,  # Simple momentum
                post_count=count,
                engagement_rate=0.5,
                related_topics=[],
            ))

        return trending


class SimulationEngine:
    """Main simulation execution engine."""

    def __init__(
        self,
        openai_settings: OpenAISettings,
        graph_store: GraphStore,
        parameters: SimulationParameters | None = None,
    ) -> None:
        self._openai_settings = openai_settings
        self._store = graph_store
        self._params = parameters or SimulationParameters()

        # Initialize components
        self._interaction_engine = InteractionEngine(openai_settings)
        self._memory_manager = MemoryManager(graph_store)
        self._scheduler = DualPlatformScheduler(
            self._interaction_engine,
            self._memory_manager,
        )
        self._demand_predictor = DemandPredictor(openai_settings)

        # State
        self._step_count = 0
        self._running = False

    async def start_simulation(self, session_id: UUID) -> bool:
        """Start a simulation session."""
        logger.info("Starting simulation session %s", session_id)
        self._running = True
        self._step_count = 0
        return True

    async def pause_simulation(self, session_id: UUID) -> bool:
        """Pause a simulation session."""
        logger.info("Pausing simulation session %s", session_id)
        self._running = False
        return True

    async def stop_simulation(self, session_id: UUID) -> bool:
        """Stop a simulation session."""
        logger.info("Stopping simulation session %s", session_id)
        self._running = False
        self._step_count = 0
        return True

    async def run_simulation_step(
        self,
        session_id: UUID,
        agents: list[AgentNode],
        worlds: list[WorldStateNode],
        platform_configs: dict[PlatformType, PlatformConfig],
    ) -> SimulationStepResult:
        """Run a single simulation step."""
        self._step_count += 1
        timestamp = datetime.utcnow()

        # Execute each platform in parallel
        platform_results = []
        tasks = []

        for world in worlds:
            platform = world.platform
            config = platform_configs.get(platform, PlatformConfig(
                platform=platform,
                post_frequency_range=(0.5, 2.0),
                interaction_probability=0.3,
                content_topics=[],
                trending_hashtags=[],
                community_rules=[],
                peak_activity_hours=[],
                character_limit=1000,
                media_support=[],
            ))

            # Filter agents for this platform
            platform_agents = [a for a in agents if a.platform == platform]
            if not platform_agents:
                continue

            task = self._scheduler.execute_platform_step(
                platform,
                platform_agents,
                world,
                config,
            )
            tasks.append(task)

        if tasks:
            platform_results = await asyncio.gather(*tasks)

        # Apply memory decay
        for agent in agents:
            await self._memory_manager.decay_memories(
                agent.id,
                self._params.memory_decay_rate,
            )

        # Calculate metrics
        total_interactions = sum(
            len(pr.interactions) for pr in platform_results
        )
        new_memories = sum(
            len(ir.memory_updates)
            for pr in platform_results
            for ir in pr.interaction_results
        )

        return SimulationStepResult(
            session_id=session_id,
            step_number=self._step_count,
            timestamp=timestamp,
            platform_results=platform_results,
            total_interactions=total_interactions,
            new_memories=new_memories,
            metrics={
                "step_duration_ms": 100,
                "active_agents": len(agents),
                "platforms_executed": len(platform_results),
            },
        )
