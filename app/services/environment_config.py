"""Environment Configuration Agent.

Configures the simulation environment including:
- World state initialization
- Platform-specific settings
- Simulation parameters injection
- Interaction rules definition
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from langchain_openai import ChatOpenAI

from app.config import OpenAISettings
from app.domain.relationships import GraphRelationship
from app.domain.social.enums import PlatformType, SimulationStatus
from app.domain.social.nodes import (
    SimulationSessionNode,
    WorldStateNode,
)
from app.exceptions import LLMExtractionError

logger = logging.getLogger(__name__)


@dataclass
class PlatformConfig:
    """Platform-specific configuration."""

    platform: PlatformType
    post_frequency_range: tuple[float, float]  # Posts per day
    interaction_probability: float
    content_topics: list[str]
    trending_hashtags: list[str]
    community_rules: list[str]
    peak_activity_hours: list[int]  # 0-23
    character_limit: int
    media_support: list[str]


@dataclass
class SimulationParameters:
    """Simulation execution parameters."""

    max_agents: int = 50
    memory_decay_rate: float = 0.1
    interaction_probability: float = 0.3
    platform_sync_interval: int = 60  # seconds
    simulation_speed: float = 1.0  # 1.0 = real-time
    enable_emotion: bool = True
    enable_memory_formation: bool = True
    enable_relationship_evolution: bool = True
    enable_content_generation: bool = True
    max_interactions_per_step: int = 10


@dataclass
class InteractionRule:
    """Rule governing agent interactions."""

    rule_type: str  # FRIEND_REQUEST, MESSAGE, POST_COMMENT, SHARE, etc.
    conditions: dict
    priority: int = 0
    weight: float = 1.0


@dataclass
class WorldConfigurationResult:
    """Result of world configuration."""

    world_state: WorldStateNode
    platform_config: PlatformConfig | None
    simulation_params: SimulationParameters
    interaction_rules: list[InteractionRule]


@dataclass
class SimulationBootstrapResult:
    """Result of full simulation bootstrap."""

    session: SimulationSessionNode
    world_states: list[WorldStateNode]
    platform_configs: dict[PlatformType, PlatformConfig]
    parameters: SimulationParameters


# Default platform configurations
DEFAULT_WECHAT_CONFIG = PlatformConfig(
    platform=PlatformType.WECHAT,
    post_frequency_range=(0.5, 3.0),
    interaction_probability=0.4,
    content_topics=["daily_life", "work", "family", "news", "hobbies"],
    trending_hashtags=[],
    community_rules=[
        "Be respectful to others",
        "No spam or excessive self-promotion",
        "Keep discussions relevant",
    ],
    peak_activity_hours=[8, 9, 12, 13, 20, 21, 22],
    character_limit=1500,
    media_support=["image", "video", "link"],
)

DEFAULT_XIAOHONGSHU_CONFIG = PlatformConfig(
    platform=PlatformType.XIAOHONGSHU,
    post_frequency_range=(0.3, 2.0),
    interaction_probability=0.5,
    content_topics=["lifestyle", "beauty", "fashion", "travel", "food", "shopping"],
    trending_hashtags=[],
    community_rules=[
        "Share authentic experiences",
        "Use relevant hashtags",
        "Include photos when possible",
        "Be helpful to the community",
    ],
    peak_activity_hours=[9, 10, 11, 20, 21, 22, 23],
    character_limit=1000,
    media_support=["image", "video", "tag"],
)


class EnvironmentConfigAgent:
    """Agent for configuring simulation environment.

    This agent:
    1. Initializes world states for platforms
    2. Configures platform-specific settings
    3. Injects simulation parameters
    4. Defines interaction rules
    5. Creates simulation sessions

    Args:
        openai_settings: OpenAI API configuration
    """

    def __init__(self, openai_settings: OpenAISettings) -> None:
        self._llm = ChatOpenAI(
            api_key=openai_settings.api_key,
            base_url=openai_settings.base_url,
            model=openai_settings.model,
            temperature=0.3,
        )
        self._settings = openai_settings

    def configure_world(
        self,
        world_key: str,
        name: str,
        description: str = "",
        platform: PlatformType = PlatformType.WECHAT,
        state_data: dict | None = None,
        platform_config: PlatformConfig | None = None,
    ) -> WorldConfigurationResult:
        """Configure a simulation world.

        Args:
            world_key: Unique world identifier
            name: World name
            description: World description
            platform: Target platform
            state_data: Initial state data
            platform_config: Optional custom platform config

        Returns:
            WorldConfigurationResult
        """
        # Create world state node
        world_state = WorldStateNode(
            world_key=world_key,
            name=name,
            definition=description,
            platform=platform,
            state_data=state_data or {},
        )

        # Use default or custom platform config
        effective_config = platform_config or self._get_default_config(platform)

        # Generate default interaction rules
        interaction_rules = self._generate_default_rules(platform, effective_config)

        # Default simulation parameters
        sim_params = SimulationParameters()

        return WorldConfigurationResult(
            world_state=world_state,
            platform_config=effective_config,
            simulation_params=sim_params,
            interaction_rules=interaction_rules,
        )

    def _get_default_config(self, platform: PlatformType) -> PlatformConfig:
        """Get default platform configuration."""
        if platform == PlatformType.WECHAT:
            return DEFAULT_WECHAT_CONFIG
        elif platform == PlatformType.XIAOHONGSHU:
            return DEFAULT_XIAOHONGSHU_CONFIG
        else:
            return DEFAULT_WECHAT_CONFIG

    def _generate_default_rules(
        self, platform: PlatformType, config: PlatformConfig
    ) -> list[InteractionRule]:
        """Generate default interaction rules for a platform."""
        rules = [
            InteractionRule(
                rule_type="VIEW_CONTENT",
                conditions={"requires_connection": False},
                priority=1,
                weight=1.0,
            ),
            InteractionRule(
                rule_type="LIKE_CONTENT",
                conditions={"requires_connection": False, "probability": config.interaction_probability},
                priority=2,
                weight=0.8,
            ),
            InteractionRule(
                rule_type="COMMENT_CONTENT",
                conditions={"requires_connection": False, "probability": config.interaction_probability * 0.3},
                priority=2,
                weight=0.5,
            ),
            InteractionRule(
                rule_type="SHARE_CONTENT",
                conditions={"requires_connection": False, "probability": config.interaction_probability * 0.1},
                priority=3,
                weight=0.3,
            ),
            InteractionRule(
                rule_type="SEND_MESSAGE",
                conditions={"requires_connection": True, "probability": config.interaction_probability * 0.5},
                priority=2,
                weight=0.6,
            ),
            InteractionRule(
                rule_type="FOLLOW_USER",
                conditions={"requires_connection": False, "probability": config.interaction_probability * 0.2},
                priority=3,
                weight=0.4,
            ),
        ]
        return rules

    def inject_simulation_parameters(
        self,
        session_node: SimulationSessionNode,
        parameters: SimulationParameters,
    ) -> SimulationSessionNode:
        """Inject simulation parameters into a session.

        Args:
            session_node: Session node to update
            parameters: Simulation parameters

        Returns:
            Updated SimulationSessionNode
        """
        # Create a new immutable node with updated parameters
        return SimulationSessionNode(
            name=session_node.name,
            definition=session_node.definition,
            session_id=session_node.session_id,
            status=session_node.status,
            start_time=session_node.start_time,
            end_time=session_node.end_time,
            parameters=parameters.__dict__,
            metrics=session_node.metrics,
            world_ids=session_node.world_ids,
            agent_ids=session_node.agent_ids,
            seed_ids=session_node.seed_ids,
        )

    def setup_platform_config(
        self,
        platform: str,
        custom_config: dict | None = None,
    ) -> PlatformConfig:
        """Setup platform configuration.

        Args:
            platform: Platform name (WECHAT or XIAOHONGSHU)
            custom_config: Optional custom configuration overrides

        Returns:
            PlatformConfig
        """
        platform_type = PlatformType(platform)
        base_config = self._get_default_config(platform_type)

        if custom_config:
            # Apply overrides
            return PlatformConfig(
                platform=base_config.platform,
                post_frequency_range=custom_config.get(
                    "post_frequency_range", base_config.post_frequency_range
                ),
                interaction_probability=custom_config.get(
                    "interaction_probability", base_config.interaction_probability
                ),
                content_topics=custom_config.get("content_topics", base_config.content_topics),
                trending_hashtags=custom_config.get(
                    "trending_hashtags", base_config.trending_hashtags
                ),
                community_rules=custom_config.get("community_rules", base_config.community_rules),
                peak_activity_hours=custom_config.get(
                    "peak_activity_hours", base_config.peak_activity_hours
                ),
                character_limit=custom_config.get("character_limit", base_config.character_limit),
                media_support=custom_config.get("media_support", base_config.media_support),
            )

        return base_config

    def define_interaction_rules(
        self,
        rules_config: list[dict],
    ) -> list[InteractionRule]:
        """Define custom interaction rules.

        Args:
            rules_config: List of rule configurations

        Returns:
            List of InteractionRule
        """
        rules = []
        for config in rules_config:
            rule = InteractionRule(
                rule_type=config.get("rule_type", "GENERAL"),
                conditions=config.get("conditions", {}),
                priority=config.get("priority", 0),
                weight=float(config.get("weight", 1.0)),
            )
            rules.append(rule)

        # Sort by priority
        rules.sort(key=lambda r: r.priority)
        return rules

    async def bootstrap_simulation(
        self,
        name: str,
        description: str = "",
        platforms: list[str] | None = None,
        parameters: SimulationParameters | None = None,
        state_data: dict | None = None,
    ) -> SimulationBootstrapResult:
        """Bootstrap a full simulation with multiple platforms.

        Args:
            name: Simulation name
            description: Simulation description
            platforms: List of platform names (default: ["WECHAT"])
            parameters: Simulation parameters
            state_data: Initial state data

        Returns:
            SimulationBootstrapResult
        """
        if platforms is None:
            platforms = ["WECHAT"]

        sim_params = parameters or SimulationParameters()

        # Create simulation session
        session = SimulationSessionNode(
            name=name,
            definition=description,
            status=SimulationStatus.INITIALIZING,
            parameters=sim_params.__dict__,
        )

        # Create world states for each platform
        world_states = []
        platform_configs = {}

        for platform_name in platforms:
            platform = PlatformType(platform_name)
            config = self._get_default_config(platform)
            platform_configs[platform] = config

            world_state = WorldStateNode(
                world_key=f"{name.lower()}_{platform.value.lower()}",
                name=f"{name} - {platform.value}",
                description=description,
                platform=platform,
                state_data={
                    "platform_config": config.__dict__,
                    "initial_state": state_data or {},
                },
            )
            world_states.append(world_state)

        return SimulationBootstrapResult(
            session=session,
            world_states=world_states,
            platform_configs=platform_configs,
            parameters=sim_params,
        )
