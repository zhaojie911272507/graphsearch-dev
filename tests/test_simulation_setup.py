"""Tests for social simulation environment setup agents.

Tests for:
- SeedExtractorAgent: Reality seed extraction
- ProfileGeneratorAgent: Agent profile generation
- EnvironmentConfigAgent: World configuration
- SimulationOrchestrator: Full bootstrap orchestration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.domain.social.enums import (
    AgentState,
    EmotionType,
    MemoryType,
    PlatformType,
    SeedSourceType,
    SimulationStatus,
)
from app.domain.social.nodes import (
    AgentNode,
    AgentProfile,
    MemoryNode,
    PersonalityTraits,
    SeedNode,
    SimulationSessionNode,
    WorldStateNode,
)
from app.services.seed_extractor import SeedExtractorAgent, SeedExtractionResult
from app.services.profile_generator import ProfileGeneratorAgent, ProfileGenerationResult
from app.services.environment_config import (
    EnvironmentConfigAgent,
    PlatformConfig,
    SimulationParameters,
)


# ──────────────────────────────────────────
# Seed Extractor Tests
# ──────────────────────────────────────────


class TestSeedExtractorAgent:
    """Tests for SeedExtractorAgent."""

    @pytest.fixture
    def openai_settings(self):
        """Mock OpenAI settings."""
        mock_settings = MagicMock()
        mock_settings.api_key = "test-key"
        mock_settings.base_url = "https://api.test.com/v1"
        mock_settings.model = "gpt-4o"
        return mock_settings

    @pytest.fixture
    def extractor(self, openai_settings):
        """Create extractor agent."""
        return SeedExtractorAgent(openai_settings)

    def test_extract_seed_empty_content(self, extractor):
        """Test extraction with empty content."""
        # Empty content should return minimal result
        pass  # Would need async test

    def test_seed_node_creation(self):
        """Test SeedNode creation from extraction."""
        seed = SeedNode(
            title="Test Seed",
            source_url="https://example.com",
            source_type=SeedSourceType.URL,
            raw_content="Test content",
        )

        assert seed.title == "Test Seed"
        assert seed.source_type == SeedSourceType.URL
        assert seed.raw_content == "Test content"
        assert seed.credibility_score == 0.5  # Default

    def test_seed_node_serialization(self):
        """Test SeedNode neo4j_properties serialization."""
        seed = SeedNode(
            title="Test Seed",
            source_type=SeedSourceType.TEXT,
            raw_content="Test content",
        )

        props = seed.neo4j_properties()

        assert props["title"] == "Test Seed"
        assert props["source_type"] == "TEXT"
        assert props["raw_content"] == "Test content"
        assert "id" in props
        assert "node_type" in props


# ──────────────────────────────────────────
# Profile Generator Tests
# ──────────────────────────────────────────


class TestProfileGeneratorAgent:
    """Tests for ProfileGeneratorAgent."""

    @pytest.fixture
    def openai_settings(self):
        """Mock OpenAI settings."""
        mock_settings = MagicMock()
        mock_settings.api_key = "test-key"
        mock_settings.base_url = "https://api.test.com/v1"
        mock_settings.model = "gpt-4o"
        return mock_settings

    @pytest.fixture
    def generator(self, openai_settings):
        """Create generator agent."""
        return ProfileGeneratorAgent(openai_settings)

    def test_agent_profile_creation(self):
        """Test AgentNode creation."""
        profile = AgentProfile(
            display_name="Test User",
            bio="A test user",
            occupation="Engineer",
            interests=["coding", "reading"],
        )

        personality = PersonalityTraits(
            openness=0.8,
            conscientiousness=0.7,
            extraversion=0.5,
            agreeableness=0.6,
            neuroticism=0.3,
        )

        agent = AgentNode(
            name="Test Agent",
            description="A test agent",
            profile=profile,
            personality=personality,
            background_story="Once upon a time...",
            goals=["Learn Python", "Build cool stuff"],
            platform=PlatformType.WECHAT,
        )

        assert agent.name == "Test Agent"
        assert agent.profile.display_name == "Test User"
        assert agent.personality.openness == 0.8
        assert agent.platform == PlatformType.WECHAT
        assert len(agent.goals) == 2

    def test_memory_creation(self):
        """Test MemoryNode creation."""
        memory = MemoryNode(
            name="First Day at Work",
            definition="A memorable day",
            content="I remember my first day at the new company...",
            memory_type=MemoryType.EPISODIC,
            importance=0.8,
            emotion_tags=[EmotionType.JOY, EmotionType.SURPRISE],
        )

        assert memory.memory_type == MemoryType.EPISODIC
        assert memory.importance == 0.8
        assert EmotionType.JOY in memory.emotion_tags
        assert EmotionType.SURPRISE in memory.emotion_tags

    def test_agent_serialization(self):
        """Test AgentNode neo4j_properties serialization."""
        profile = AgentProfile(display_name="Test", occupation="Dev")
        personality = PersonalityTraits()

        agent = AgentNode(
            name="Test Agent",
            profile=profile,
            personality=personality,
            platform=PlatformType.WECHAT,
        )

        props = agent.neo4j_properties()

        assert props["name"] == "Test Agent"
        assert props["platform"] == "WECHAT"
        assert "profile" in props  # JSON string
        assert "personality" in props  # JSON string


# ──────────────────────────────────────────
# Environment Config Tests
# ──────────────────────────────────────────


class TestEnvironmentConfigAgent:
    """Tests for EnvironmentConfigAgent."""

    @pytest.fixture
    def openai_settings(self):
        """Mock OpenAI settings."""
        mock_settings = MagicMock()
        mock_settings.api_key = "test-key"
        mock_settings.base_url = "https://api.test.com/v1"
        mock_settings.model = "gpt-4o"
        return mock_settings

    @pytest.fixture
    def config_agent(self, openai_settings):
        """Create config agent."""
        return EnvironmentConfigAgent(openai_settings)

    def test_platform_config_defaults(self):
        """Test default platform configuration."""
        from app.services.environment_config import (
            DEFAULT_WECHAT_CONFIG,
            DEFAULT_XIAOHONGSHU_CONFIG,
        )

        # WeChat defaults
        assert DEFAULT_WECHAT_CONFIG.platform == PlatformType.WECHAT
        assert DEFAULT_WECHAT_CONFIG.interaction_probability == 0.4
        assert "daily_life" in DEFAULT_WECHAT_CONFIG.content_topics

        # Xiaohongshu defaults
        assert DEFAULT_XIAOHONGSHU_CONFIG.platform == PlatformType.XIAOHONGSHU
        assert DEFAULT_XIAOHONGSHU_CONFIG.interaction_probability == 0.5
        assert "lifestyle" in DEFAULT_XIAOHONGSHU_CONFIG.content_topics

    def test_world_state_creation(self, config_agent):
        """Test WorldStateNode creation."""
        result = config_agent.configure_world(
            world_key="test_world",
            name="Test World",
            description="A test simulation world",
            platform=PlatformType.WECHAT,
        )

        assert result.world_state.world_key == "test_world"
        assert result.world_state.name == "Test World"
        assert result.world_state.platform == PlatformType.WECHAT
        assert result.platform_config is not None

    def test_simulation_parameters(self):
        """Test SimulationParameters."""
        params = SimulationParameters(
            max_agents=100,
            memory_decay_rate=0.15,
            interaction_probability=0.4,
            enable_emotion=True,
        )

        assert params.max_agents == 100
        assert params.memory_decay_rate == 0.15
        assert params.interaction_probability == 0.4
        assert params.enable_emotion is True

    def test_interaction_rules_generation(self, config_agent):
        """Test interaction rules generation."""
        from app.services.environment_config import DEFAULT_WECHAT_CONFIG

        rules = config_agent._generate_default_rules(
            PlatformType.WECHAT,
            DEFAULT_WECHAT_CONFIG,
        )

        assert len(rules) >= 5  # At least default rules
        rule_types = [r.rule_type for r in rules]
        assert "VIEW_CONTENT" in rule_types
        assert "LIKE_CONTENT" in rule_types
        assert "COMMENT_CONTENT" in rule_types

    def test_custom_platform_config(self, config_agent):
        """Test custom platform configuration."""
        custom = {
            "interaction_probability": 0.8,
            "content_topics": ["custom_topic"],
            "character_limit": 500,
        }

        config = config_agent.setup_platform_config("WECHAT", custom)

        assert config.interaction_probability == 0.8
        assert "custom_topic" in config.content_topics
        assert config.character_limit == 500


# ──────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────


class TestSimulationOrchestrator:
    """Integration tests for SimulationOrchestrator."""

    @pytest.fixture
    def openai_settings(self):
        """Mock OpenAI settings."""
        mock_settings = MagicMock()
        mock_settings.api_key = "test-key"
        mock_settings.base_url = "https://api.test.com/v1"
        mock_settings.model = "gpt-4o"
        return mock_settings

    @pytest.fixture
    def mock_graph_store(self):
        """Mock graph store."""
        store = AsyncMock()
        store.merge_nodes = AsyncMock(return_value=None)
        store.merge_relationships = AsyncMock(return_value=None)
        return store

    def test_bootstrap_config_creation(self):
        """Test SimulationBootstrapConfig."""
        from app.services.simulation_orchestrator import SimulationBootstrapConfig

        config = SimulationBootstrapConfig(
            name="Test Simulation",
            description="A test",
            agent_count=20,
            platforms=["WECHAT", "XIAOHONGSHU"],
        )

        assert config.name == "Test Simulation"
        assert config.agent_count == 20
        assert len(config.platforms) == 2
        assert "WECHAT" in config.platforms

    def test_world_state_node(self):
        """Test WorldStateNode."""
        world = WorldStateNode(
            world_key="wechat_world",
            name="WeChat World",
            definition="A WeChat simulation",
            platform=PlatformType.WECHAT,
        )

        props = world.neo4j_properties()

        assert props["world_key"] == "wechat_world"
        assert props["platform"] == "WECHAT"
        assert "state_data" in props

    def test_simulation_session_node(self):
        """Test SimulationSessionNode."""
        session = SimulationSessionNode(
            name="Test Session",
            definition="A test session",
            status=SimulationStatus.RUNNING,
            parameters={"max_agents": 50},
        )

        props = session.neo4j_properties()

        assert props["name"] == "Test Session"
        assert props["status"] == "RUNNING"
        assert props["parameters"] == {"max_agents": 50}
