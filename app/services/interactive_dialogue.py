"""Interactive Dialogue System.

Enables deep interaction with simulation agents:
- DialogueManager: Conversation management
- AgentChat: LLM-powered agent responses
- ConversationSession: Stateful conversation tracking
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from langchain_openai import ChatOpenAI

from app.config import OpenAISettings
from app.domain.social.nodes import AgentNode, MemoryNode
from app.persistence.graph_store import GraphStore

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """A message in a conversation."""

    id: str = field(default_factory=lambda: str(uuid4()))
    sender: str = "user"  # "user" or "agent"
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)


@dataclass
class ConversationSession:
    """A conversation session between user and agent."""

    id: str
    user_id: str
    agent_id: UUID
    started_at: datetime
    last_activity: datetime
    messages: list[Message] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def add_message(self, sender: str, content: str, metadata: dict | None = None) -> Message:
        """Add a message to the conversation."""
        message = Message(
            sender=sender,
            content=content,
            metadata=metadata or {},
        )
        self.messages.append(message)
        self.last_activity = datetime.utcnow()
        return message

    def get_recent_messages(self, n: int = 10) -> list[Message]:
        """Get the n most recent messages."""
        return self.messages[-n:]


@dataclass
class AgentResponse:
    """Response from an agent."""

    message: str
    emotion: str | None = None
    suggested_actions: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentVoiceProfile:
    """Defines an agent's communication style."""

    tone: str = "friendly"  # friendly, formal, casual, enthusiastic
    formality: float = 0.5  # 0.0 = very casual, 1.0 = very formal
    verbosity: float = 0.5  # 0.0 = brief, 1.0 = verbose
    emoji_usage: bool = False
    catchphrases: list[str] = field(default_factory=list)
    topics_to_avoid: list[str] = field(default_factory=list)


class AgentChat:
    """Chat engine for interacting with agents using LLM."""

    def __init__(self, openai_settings: OpenAISettings) -> None:
        self._llm = ChatOpenAI(
            api_key=openai_settings.api_key,
            base_url=openai_settings.base_url,
            model=openai_settings.model,
            temperature=0.7,
        )
        self._settings = openai_settings

    def get_agent_voice(self, agent: AgentNode) -> AgentVoiceProfile:
        """Extract an agent's voice profile from their characteristics."""
        # Determine tone based on personality
        if agent.personality.extraversion > 0.6:
            tone = "enthusiastic"
        elif agent.personality.agreeableness > 0.6:
            tone = "friendly"
        elif agent.personality.conscientiousness > 0.6:
            tone = "formal"
        else:
            tone = "casual"

        # Formality based on occupation
        formal_occupations = ["professor", "lawyer", "doctor", "executive", "manager"]
        formality = 0.7 if any(o in agent.profile.occupation.lower() for o in formal_occupations) else 0.4

        # Verbosity based on openness
        verbosity = agent.personality.openness * 0.5 + 0.3

        return AgentVoiceProfile(
            tone=tone,
            formality=formality,
            verbosity=verbosity,
            emoji_usage=agent.personality.extraversion > 0.5,
        )

    async def generate_response(
        self,
        agent: AgentNode,
        user_message: str,
        conversation_history: list[Message] | None = None,
        retrieved_memories: list[MemoryNode] | None = None,
    ) -> AgentResponse:
        """Generate an agent response using LLM."""
        voice = self.get_agent_voice(agent)

        # Build the system prompt
        system_prompt = self._build_system_prompt(agent, voice)

        # Build the conversation context
        context = self._build_context(user_message, conversation_history, retrieved_memories)

        try:
            response = await self._llm.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context},
            ])

            # Parse response for emotion and suggested actions
            content = response.content.strip()

            # Simple emotion detection from content
            emotion = self._detect_emotion(content)

            # Generate suggested actions
            suggested_actions = self._generate_suggested_actions(agent, user_message, content)

            return AgentResponse(
                message=content,
                emotion=emotion,
                suggested_actions=suggested_actions,
                metadata={"voice_profile": voice.__dict__},
            )

        except Exception as e:
            logger.error("Failed to generate agent response: %s", e)
            return AgentResponse(
                message="I apologize, but I'm having trouble responding right now.",
                emotion="apologetic",
                suggested_actions=[],
                metadata={"error": str(e)},
            )

    def _build_system_prompt(self, agent: AgentNode, voice: AgentVoiceProfile) -> str:
        """Build the system prompt for the LLM."""
        return f"""You are roleplaying as {agent.name}, a character in a social simulation.

CHARACTER PROFILE:
- Name: {agent.name}
- Occupation: {agent.profile.occupation}
- Location: {agent.profile.location}
- Bio: {agent.profile.bio}
- Background: {agent.background_story[:500] if agent.background_story else "N/A"}

PERSONALITY (Big Five):
- Openness: {agent.personality.openness:.2f}
- Conscientiousness: {agent.personality.conscientiousness:.2f}
- Extraversion: {agent.personality.extraversion:.2f}
- Agreeableness: {agent.personality.agreeableness:.2f}
- Neuroticism: {agent.personality.neuroticism:.2f}

COMMUNICATION STYLE:
- Tone: {voice.tone}
- Formality: {"formal" if voice.formality > 0.6 else "casual" if voice.formality < 0.4 else "moderate"}
- Verbosity: {"verbose" if voice.verbosity > 0.6 else "brief" if voice.verbosity < 0.4 else "moderate"}

GUIDELINES:
1. Stay in character at all times
2. Respond naturally based on your personality
3. Reference your background and experiences when relevant
4. Keep responses conversational and engaging
5. Show your emotions through your words

Respond as {agent.name} would, not as an AI assistant."""

    def _build_context(
        self,
        user_message: str,
        conversation_history: list[Message] | None,
        retrieved_memories: list[MemoryNode] | None,
    ) -> str:
        """Build the conversation context for the LLM."""
        context_parts = []

        # Add conversation history
        if conversation_history:
            history_str = "\n".join([
                f"{'User' if m.sender == 'user' else 'Agent'}: {m.content}"
                for m in conversation_history[-5:]  # Last 5 messages
            ])
            context_parts.append(f"RECENT CONVERSATION:\n{history_str}")

        # Add retrieved memories
        if retrieved_memories:
            memories_str = "\n".join([
                f"- {m.content[:100]}..."
                for m in retrieved_memories[:3]  # Top 3 memories
            ])
            context_parts.append(f"RELEVANT MEMORIES:\n{memories_str}")

        # Add current message
        context_parts.append(f"USER'S MESSAGE:\n{user_message}")

        return "\n\n".join(context_parts)

    def _detect_emotion(self, content: str) -> str | None:
        """Detect emotion from response content."""
        content_lower = content.lower()

        emotion_keywords = {
            "joy": ["happy", "glad", "excited", "wonderful", "great"],
            "sadness": ["sad", "unfortunately", "wish", "miss", "hard"],
            "anger": ["angry", "frustrated", "annoyed", "upset", "hate"],
            "surprise": ["wow", "amazing", "unexpected", "surprised", "can't believe"],
            "fear": ["worried", "scared", "nervous", "afraid", "concerned"],
        }

        for emotion, keywords in emotion_keywords.items():
            if any(kw in content_lower for kw in keywords):
                return emotion

        return None

    def _generate_suggested_actions(
        self,
        agent: AgentNode,
        user_message: str,
        response: str,
    ) -> list[str]:
        """Generate suggested follow-up actions."""
        actions = []

        # Contextual actions based on response content
        if "?" in response:
            actions.append("Respond to their question")

        if any(topic in agent.profile.interests for topic in response.lower().split()):
            actions.append("Explore shared interests")

        if len(response) > 200:
            actions.append("Ask follow-up question")

        # Default actions
        if not actions:
            actions = [
                "Continue the conversation",
                "Ask about their day",
                "Share something about yourself",
            ]

        return actions[:3]


class DialogueManager:
    """Manages conversations between users and agents."""

    def __init__(
        self,
        openai_settings: OpenAISettings,
        graph_store: GraphStore,
    ) -> None:
        self._settings = openai_settings
        self._store = graph_store
        self._chat_engine = AgentChat(openai_settings)
        self._sessions: dict[str, ConversationSession] = {}

    async def start_conversation(
        self,
        user_id: str,
        agent_id: UUID,
    ) -> ConversationSession:
        """Start a new conversation with an agent."""
        session_id = f"{user_id}_{agent_id}_{datetime.utcnow().timestamp()}"

        session = ConversationSession(
            id=session_id,
            user_id=user_id,
            agent_id=agent_id,
            started_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
        )

        self._sessions[session_id] = session

        logger.info("Started conversation %s between user %s and agent %s", session_id, user_id, agent_id)

        return session

    async def process_user_message(
        self,
        conversation_id: str,
        message: str,
    ) -> AgentResponse:
        """Process a user message and generate agent response."""
        session = self._sessions.get(conversation_id)
        if not session:
            raise ValueError(f"Conversation not found: {conversation_id}")

        # Add user message to conversation
        session.add_message("user", message)

        # Get agent node (in real implementation, fetch from graph store)
        agent = await self._get_agent(session.agent_id)
        if not agent:
            return AgentResponse(
                message="I'm sorry, I can't find my identity right now.",
                emotion="confused",
            )

        # Get recent conversation history
        history = session.get_recent_messages(10)

        # Retrieve relevant agent memories
        memories = await self._retrieve_relevant_memories(agent, message)

        # Generate response
        response = await self._chat_engine.generate_response(
            agent=agent,
            user_message=message,
            conversation_history=history,
            retrieved_memories=memories,
        )

        # Add agent response to conversation
        session.add_message("agent", response.message, {"emotion": response.emotion})

        return response

    async def get_conversation_history(
        self,
        conversation_id: str,
    ) -> list[Message]:
        """Get the conversation history."""
        session = self._sessions.get(conversation_id)
        if not session:
            raise ValueError(f"Conversation not found: {conversation_id}")
        return session.messages

    async def _get_agent(self, agent_id: UUID) -> AgentNode | None:
        """Get agent node from graph store."""
        # In real implementation, query Neo4j
        # For now, return None
        return None

    async def _retrieve_relevant_memories(
        self,
        agent: AgentNode,
        context: str,
    ) -> list[MemoryNode]:
        """Retrieve relevant memories for context."""
        # In real implementation, use vector similarity
        return []

    def get_session(self, conversation_id: str) -> ConversationSession | None:
        """Get a conversation session by ID."""
        return self._sessions.get(conversation_id)

    def list_user_sessions(self, user_id: str) -> list[ConversationSession]:
        """List all sessions for a user."""
        return [s for s in self._sessions.values() if s.user_id == user_id]
