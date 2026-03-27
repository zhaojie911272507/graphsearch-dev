"""Tests for social simulation execution and report generation.

Tests for:
- SimulationEngine: Core execution engine
- InteractionEngine: Agent interactions
- MemoryManager: Temporal memory management
- DemandPredictor: Need prediction
- ReportAgent: Report generation
- DialogueManager: Interactive dialogue
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.domain.social.enums import (
    AgentState,
    EmotionType,
    InteractionType,
    MemoryType,
    PlatformType,
    ReportType,
    NeedType,
    SimulationStatus,
)
from app.domain.social.nodes import (
    AgentNode,
    AgentProfile,
    MemoryNode,
    PersonalityTraits,
    InteractionNode,
    ReportNode,
)
from app.services.simulation_execution import (
    Interaction,
    InteractionEngine,
    MemoryManager,
    DemandPredictor,
    DualPlatformScheduler,
    SimulationEngine,
)
from app.services.report_generation import ReportAgent, SimulationReport
from app.services.interactive_dialogue import (
    Message,
    ConversationSession,
    AgentChat,
    DialogueManager,
)


# ──────────────────────────────────────────
# Test Fixtures
# ──────────────────────────────────────────


@pytest.fixture
def openai_settings():
    """Mock OpenAI settings."""
    mock_settings = MagicMock()
    mock_settings.api_key = "test-key"
    mock_settings.base_url = "https://api.test.com/v1"
    mock_settings.model = "gpt-4o"
    return mock_settings


@pytest.fixture
def mock_graph_store():
    """Mock graph store."""
    store = AsyncMock()
    store.merge_nodes = AsyncMock(return_value=None)
    store.merge_relationships = AsyncMock(return_value=None)
    return store


@pytest.fixture
def sample_agent():
    """Create a sample agent for testing."""
    profile = AgentProfile(
        display_name="Test User",
        bio="A test user",
        occupation="Software Engineer",
        location="Beijing",
        interests=["coding", "reading", "music"],
    )

    personality = PersonalityTraits(
        openness=0.8,
        conscientiousness=0.7,
        extraversion=0.6,
        agreeableness=0.7,
        neuroticism=0.3,
    )

    return AgentNode(
        name="Test Agent",
        description="A test agent for simulation",
        profile=profile,
        personality=personality,
        background_story="Once upon a time, there was a software engineer...",
        goals=["Build great software", "Help others"],
        platform=PlatformType.WECHAT,
    )


# ──────────────────────────────────────────
# Interaction Tests
# ──────────────────────────────────────────


class TestInteraction:
    """Tests for Interaction dataclass."""

    def test_interaction_creation(self, sample_agent):
        """Test creating an interaction."""
        interaction = Interaction(
            interaction_type=InteractionType.POST,
            sender=sample_agent,
            receiver=None,
            content="Hello world!",
            priority=0.8,
        )

        assert interaction.interaction_type == InteractionType.POST
        assert interaction.sender == sample_agent
        assert interaction.receiver is None
        assert interaction.content == "Hello world!"
        assert interaction.priority == 0.8


class TestInteractionEngine:
    """Tests for InteractionEngine."""

    @pytest.fixture
    def engine(self, openai_settings):
        """Create interaction engine."""
        return InteractionEngine(openai_settings)

    def test_engine_initialization(self, engine):
        """Test engine initialization."""
        assert engine._llm is not None
        assert engine._settings is not None


class TestMemoryManager:
    """Tests for MemoryManager."""

    @pytest.fixture
    def memory_manager(self, mock_graph_store):
        """Create memory manager."""
        return MemoryManager(mock_graph_store)

    def test_memory_manager_initialization(self, memory_manager):
        """Test memory manager initialization."""
        assert memory_manager._store is not None


# ──────────────────────────────────────────
# Demand Predictor Tests
# ──────────────────────────────────────────


class TestDemandPredictor:
    """Tests for DemandPredictor."""

    @pytest.fixture
    def predictor(self, openai_settings):
        """Create demand predictor."""
        return DemandPredictor(openai_settings)

    def test_predictor_initialization(self, predictor):
        """Test predictor initialization."""
        assert predictor._llm is not None


# ──────────────────────────────────────────
# Report Generation Tests
# ──────────────────────────────────────────


class TestReportAgent:
    """Tests for ReportAgent."""

    @pytest.fixture
    def report_agent(self, openai_settings, mock_graph_store):
        """Create report agent."""
        return ReportAgent(openai_settings, mock_graph_store)

    def test_report_agent_initialization(self, report_agent):
        """Test report agent initialization."""
        assert report_agent._llm is not None
        assert report_agent._store is not None

    def test_simulation_report_creation(self):
        """Test creating a simulation report."""
        report = SimulationReport(
            session_id=uuid4(),
            report_type=ReportType.DAILY_SUMMARY,
            generated_at=datetime.utcnow(),
            time_range=(datetime.utcnow() - timedelta(days=1), datetime.utcnow()),
        )

        assert report.report_type == ReportType.DAILY_SUMMARY
        assert report.total_agents == 0  # Default
        assert report.total_interactions == 0  # Default


# ──────────────────────────────────────────
# Dialogue Tests
# ──────────────────────────────────────────


class TestAgentChat:
    """Tests for AgentChat."""

    @pytest.fixture
    def agent_chat(self, openai_settings):
        """Create agent chat engine."""
        return AgentChat(openai_settings)

    def test_agent_chat_initialization(self, agent_chat):
        """Test agent chat initialization."""
        assert agent_chat._llm is not None

    def test_get_agent_voice(self, agent_chat, sample_agent):
        """Test getting agent voice profile."""
        voice = agent_chat.get_agent_voice(sample_agent)

        assert voice is not None
        assert voice.tone in ["friendly", "formal", "casual", "enthusiastic"]
        assert 0.0 <= voice.formality <= 1.0
        assert 0.0 <= voice.verbosity <= 1.0


class TestConversationSession:
    """Tests for ConversationSession."""

    def test_conversation_session_creation(self):
        """Test creating a conversation session."""
        agent_id = uuid4()
        session = ConversationSession(
            id="test_session_1",
            user_id="user_123",
            agent_id=agent_id,
            started_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
        )

        assert session.id == "test_session_1"
        assert session.user_id == "user_123"
        assert session.agent_id == agent_id
        assert len(session.messages) == 0

    def test_add_message(self):
        """Test adding messages to conversation."""
        session = ConversationSession(
            id="test_session_2",
            user_id="user_123",
            agent_id=uuid4(),
            started_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
        )

        # Add user message
        user_msg = session.add_message("user", "Hello!")
        assert len(session.messages) == 1
        assert user_msg.sender == "user"
        assert user_msg.content == "Hello!"

        # Add agent response
        agent_msg = session.add_message("agent", "Hi there!")
        assert len(session.messages) == 2
        assert agent_msg.sender == "agent"

    def test_get_recent_messages(self):
        """Test getting recent messages."""
        session = ConversationSession(
            id="test_session_3",
            user_id="user_123",
            agent_id=uuid4(),
            started_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
        )

        # Add 10 messages
        for i in range(10):
            session.add_message("user", f"Message {i}")

        # Get last 5
        recent = session.get_recent_messages(5)
        assert len(recent) == 5
        assert recent[0].content == "Message 5"  # First of the last 5


class TestDialogueManager:
    """Tests for DialogueManager."""

    @pytest.fixture
    def dialogue_manager(self, openai_settings, mock_graph_store):
        """Create dialogue manager."""
        return DialogueManager(openai_settings, mock_graph_store)

    def test_dialogue_manager_initialization(self, dialogue_manager):
        """Test dialogue manager initialization."""
        assert dialogue_manager._chat_engine is not None
        assert dialogue_manager._sessions == {}


# ──────────────────────────────────────────
# Node Tests
# ──────────────────────────────────────────


class TestInteractionNode:
    """Tests for InteractionNode."""

    def test_interaction_node_creation(self):
        """Test creating an interaction node."""
        sender_id = uuid4()
        receiver_id = uuid4()

        node = InteractionNode(
            name="Post from Test Agent",
            definition="A social media post",
            interaction_type=InteractionType.POST.value,
            content="Hello world!",
            sender_id=sender_id,
            receiver_id=None,
        )

        assert node.interaction_type == InteractionType.POST.value
        assert node.sender_id == sender_id
        assert node.receiver_id is None
        assert node.content == "Hello world!"

    def test_interaction_node_serialization(self):
        """Test interaction node neo4j_properties serialization."""
        sender_id = uuid4()

        node = InteractionNode(
            name="Test Interaction",
            interaction_type=InteractionType.COMMENT.value,
            content="Nice post!",
            sender_id=sender_id,
            interaction_metadata={},  # Use interaction_metadata instead of metadata
        )

        props = node.neo4j_properties()

        assert props["interaction_type"] == InteractionType.COMMENT.value
        assert props["content"] == "Nice post!"
        assert props["sender_id"] == str(sender_id)
        assert "id" in props
        assert "node_type" in props


class TestReportNode:
    """Tests for ReportNode."""

    def test_report_node_creation(self):
        """Test creating a report node."""
        session_id = uuid4()

        node = ReportNode(
            name="Daily Summary 2024-01-01",
            definition="Daily simulation summary",
            report_type=ReportType.DAILY_SUMMARY.value,
            session_id=session_id,
            content={"total_agents": 10, "total_interactions": 50},
            summary="A productive day in the simulation",
        )

        assert node.report_type == ReportType.DAILY_SUMMARY.value
        assert node.session_id == session_id
        assert node.content["total_agents"] == 10

    def test_report_node_serialization(self):
        """Test report node neo4j_properties serialization."""
        session_id = uuid4()

        node = ReportNode(
            name="Test Report",
            report_type=ReportType.WEEKLY_ANALYSIS.value,
            session_id=session_id,
            summary="Weekly analysis summary",
        )

        props = node.neo4j_properties()

        assert props["report_type"] == ReportType.WEEKLY_ANALYSIS.value
        assert props["session_id"] == str(session_id)
        assert props["summary"] == "Weekly analysis summary"


# ──────────────────────────────────────────
# Integration Tests
# ──────────────────────────────────────────


class TestSimulationEngine:
    """Integration tests for SimulationEngine."""

    @pytest.fixture
    def simulation_engine(self, openai_settings, mock_graph_store):
        """Create simulation engine."""
        return SimulationEngine(openai_settings, mock_graph_store)

    def test_simulation_engine_initialization(self, simulation_engine):
        """Test simulation engine initialization."""
        assert simulation_engine._interaction_engine is not None
        assert simulation_engine._memory_manager is not None
        assert simulation_engine._scheduler is not None
        assert simulation_engine._demand_predictor is not None
        assert simulation_engine._running is False
