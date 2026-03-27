"""Profile Generator Agent.

Generates detailed agent profiles including:
- Basic profile information (name, bio, occupation, etc.)
- Background stories
- Personality traits (Big Five)
- Initial memories
- Inter-agent relationships
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from langchain_openai import ChatOpenAI

from app.config import OpenAISettings
from app.domain.enums import EntityType
from app.domain.nodes import EntityNode
from app.domain.relationships import GraphRelationship
from app.domain.social.enums import EmotionType, MemoryType, PlatformType
from app.domain.social.relationships import SocialRelationType
from app.domain.social.nodes import (
    AgentNode,
    AgentProfile,
    MemoryNode,
    PersonalityTraits,
    SeedNode,
)
from app.exceptions import LLMExtractionError, LLMResponseParsingError

logger = logging.getLogger(__name__)


@dataclass
class GeneratedAgentProfile:
    """Complete generated agent profile."""

    name: str
    profile: AgentProfile
    personality: PersonalityTraits
    background_story: str
    goals: list[str]
    initial_memories: list[MemoryNode]
    entity_node: EntityNode | None = None


@dataclass
class ProfileGenerationResult:
    """Result of profile generation."""

    agents: list[AgentNode]
    memories: list[MemoryNode]
    relationships: list[GraphRelationship]
    statistics: dict = field(default_factory=dict)


# Prompt templates for profile generation
PROFILE_GENERATION_SYSTEM = """You are a character profile generator for social simulation.
Your task is to create detailed, realistic agent profiles based on the provided seed data.

For each agent, generate:
1. **Basic Profile**: Name, bio, location, occupation, interests, etc.
2. **Background Story**: A coherent life story that explains who they are
3. **Personality Traits**: Big Five traits (0.0-1.0 scale)
4. **Current Goals**: What they're trying to achieve
5. **Initial Memories**: Key memories that shape their perspective

You MUST respond with valid JSON matching this exact schema:

{
  "agents": [
    {
      "name": "string",
      "profile": {
        "display_name": "string",
        "bio": "string",
        "location": "string",
        "occupation": "string",
        "interests": ["string"],
        "social_class": "string",
        "education_level": "string",
        "relationship_status": "string",
        "values": ["string"]
      },
      "personality": {
        "openness": 0.0-1.0,
        "conscientiousness": 0.0-1.0,
        "extraversion": 0.0-1.0,
        "agreeableness": 0.0-1.0,
        "neuroticism": 0.0-1.0
      },
      "background_story": "string (2-3 paragraphs)",
      "goals": ["string"],
      "initial_memories": [
        {
          "name": "string",
          "content": "string",
          "memory_type": "EPISODIC | SEMANTIC | PROCEDURAL",
          "importance": 0.0-1.0,
          "emotion_tags": ["JOY | SADNESS | ANGER | FEAR | SURPRISE | DISGUST | NEUTRAL"]
        }
      ]
    }
  ],
  "relationships": [
    {
      "agent1_name": "string",
      "agent2_name": "string",
      "relation_type": "KNOWS | FRIENDS_WITH | FOLLOWS | FAMILY_OF | COLLEAGUE_OF | INFLUENCES",
      "weight": 0.0-1.0,
      "context": "string"
    }
  ]
}

Rules:
1. Create diverse, realistic characters that fit the seed context
2. Each agent should have distinct personality and background
3. Memories should be meaningful and relate to their background
4. Relationships should make sense given the context
5. Respond ONLY with valid JSON, no markdown"""

PROFILE_GENERATION_USER = """Based on this seed data, generate {count} diverse agent profiles:

Seed Title: {title}
Seed Content (excerpt): {content_excerpt}

Consider the context and create characters who would naturally exist in this world.
Include their relationships with each other where appropriate."""


class ProfileGeneratorAgent:
    """Agent for generating simulation agent profiles.

    This agent:
    1. Takes seed data as input
    2. Uses LLM to generate diverse character profiles
    3. Creates AgentNode objects with full profiles
    4. Generates initial memories for each agent
    5. Builds inter-agent relationships

    Args:
        openai_settings: OpenAI API configuration
    """

    def __init__(self, openai_settings: OpenAISettings) -> None:
        self._llm = ChatOpenAI(
            api_key=openai_settings.api_key,
            base_url=openai_settings.base_url,
            model=openai_settings.model,
            temperature=0.7,  # Higher temperature for creativity
            model_kwargs={"response_format": {"type": "json_object"}},
        )
        self._settings = openai_settings

    async def generate_profiles(
        self,
        seed_data: dict,
        profile_count: int = 5,
        platform: PlatformType = PlatformType.WECHAT,
    ) -> ProfileGenerationResult:
        """Generate agent profiles from seed data.

        Args:
            seed_data: Dictionary with seed information
            profile_count: Number of agents to generate
            platform: Target platform for agents

        Returns:
            ProfileGenerationResult with agents, memories, and relationships
        """
        # Prepare context for LLM
        title = seed_data.get("title", "Untitled Seed")
        content = seed_data.get("raw_content", "")[:2000]  # Truncate for context

        try:
            response = await self._llm.ainvoke(
                [
                    {"role": "system", "content": PROFILE_GENERATION_SYSTEM},
                    {
                        "role": "user",
                        "content": PROFILE_GENERATION_USER.format(
                            count=profile_count, title=title, content_excerpt=content
                        ),
                    },
                ]
            )

            raw_text = response.content
            if not isinstance(raw_text, str):
                raise LLMResponseParsingError("LLM returned non-string content")

            return self._parse_llm_response(raw_text, platform)

        except Exception as e:
            logger.warning("Profile generation failed: %s", e)
            return ProfileGenerationResult(
                agents=[],
                memories=[],
                relationships=[],
                statistics={"error": str(e)},
            )

    def _parse_llm_response(
        self, raw_json: str, platform: PlatformType
    ) -> ProfileGenerationResult:
        """Parse LLM JSON response into agent nodes and relationships.

        Args:
            raw_json: Raw JSON string from LLM
            platform: Target platform

        Returns:
            ProfileGenerationResult
        """
        import json

        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse LLM JSON: %s", e)
            return ProfileGenerationResult(
                agents=[],
                memories=[],
                relationships=[],
                statistics={"error": f"JSON parse error: {e}"},
            )

        agents = []
        all_memories = []
        relationships = []

        # Process each agent
        for agent_data in data.get("agents", []):
            agent_node, memories = self._build_agent(agent_data, platform)
            agents.append(agent_node)
            all_memories.extend(memories)

        # Process relationships
        name_to_agent = {a.name: a for a in agents}
        for rel_data in data.get("relationships", []):
            rel = self._build_relationship(rel_data, name_to_agent)
            if rel:
                relationships.append(rel)

        statistics = {
            "agent_count": len(agents),
            "memory_count": len(all_memories),
            "relationship_count": len(relationships),
            "generation_model": self._settings.model,
        }

        return ProfileGenerationResult(
            agents=agents,
            memories=all_memories,
            relationships=relationships,
            statistics=statistics,
        )

    def _build_agent(
        self, agent_data: dict, platform: PlatformType
    ) -> tuple[AgentNode, list[MemoryNode]]:
        """Build an AgentNode from parsed data.

        Args:
            agent_data: Agent data dict from LLM
            platform: Target platform

        Returns:
            Tuple of (AgentNode, list of MemoryNode)
        """
        profile_data = agent_data.get("profile", {})
        personality_data = agent_data.get("personality", {})
        memories_data = agent_data.get("initial_memories", [])

        # Build profile
        profile = AgentProfile(
            display_name=profile_data.get("display_name", agent_data.get("name", "")),
            bio=profile_data.get("bio", ""),
            location=profile_data.get("location", ""),
            occupation=profile_data.get("occupation", ""),
            interests=profile_data.get("interests", []),
            social_class=profile_data.get("social_class", ""),
            education_level=profile_data.get("education_level", ""),
            relationship_status=profile_data.get("relationship_status", ""),
            values=profile_data.get("values", []),
        )

        # Build personality
        personality = PersonalityTraits(
            openness=float(personality_data.get("openness", 0.5)),
            conscientiousness=float(personality_data.get("conscientiousness", 0.5)),
            extraversion=float(personality_data.get("extraversion", 0.5)),
            agreeableness=float(personality_data.get("agreeableness", 0.5)),
            neuroticism=float(personality_data.get("neuroticism", 0.5)),
        )

        # Build memories
        memories = []
        for mem_data in memories_data:
            memory = self._build_memory(mem_data)
            if memory:
                memories.append(memory)

        # Create agent node
        agent_node = AgentNode(
            name=agent_data.get("name", "Unknown"),
            description=f"Generated agent - {profile.occupation}" if profile.occupation else "Generated agent",
            profile=profile,
            background_story=agent_data.get("background_story", ""),
            personality=personality,
            goals=agent_data.get("goals", []),
            platform=platform,
            memory_ids=[m.id for m in memories],
        )

        return agent_node, memories

    def _build_memory(self, memory_data: dict) -> MemoryNode | None:
        """Build a MemoryNode from parsed data.

        Args:
            memory_data: Memory data dict

        Returns:
            MemoryNode or None if invalid
        """
        try:
            memory_type_str = memory_data.get("memory_type", "EPISODIC")
            memory_type = MemoryType(memory_type_str) if memory_type_str in [
                m.value for m in MemoryType
            ] else MemoryType.EPISODIC

            emotion_tags = []
            for tag_str in memory_data.get("emotion_tags", []):
                if tag_str in [e.value for e in EmotionType]:
                    emotion_tags.append(EmotionType(tag_str))

            if not emotion_tags:
                emotion_tags = [EmotionType.NEUTRAL]

            importance = memory_data.get("importance", 0.5)
            if not isinstance(importance, (int, float)):
                importance = 0.5
            importance = max(0.0, min(1.0, float(importance)))

            return MemoryNode(
                name=memory_data.get("name", "Memory"),
                definition=memory_data.get("content", "")[:500],
                content=memory_data.get("content", ""),
                memory_type=memory_type,
                importance=importance,
                emotion_tags=emotion_tags,
            )
        except Exception as e:
            logger.debug("Failed to build memory: %s", e)
            return None

    def _build_relationship(
        self, rel_data: dict, name_to_agent: dict[str, AgentNode]
    ) -> GraphRelationship | None:
        """Build a GraphRelationship between agents.

        Args:
            rel_data: Relationship data dict
            name_to_agent: Mapping of agent names to nodes

        Returns:
            GraphRelationship or None if invalid
        """
        agent1_name = rel_data.get("agent1_name", "")
        agent2_name = rel_data.get("agent2_name", "")

        agent1 = name_to_agent.get(agent1_name)
        agent2 = name_to_agent.get(agent2_name)

        if not agent1 or not agent2:
            return None

        rel_type_str = rel_data.get("relation_type", "KNOWS")
        try:
            rel_type = SocialRelationType(rel_type_str)
        except ValueError:
            rel_type = SocialRelationType.KNOWS

        weight = rel_data.get("weight", 0.5)
        if not isinstance(weight, (int, float)):
            weight = 0.5
        weight = max(0.0, min(1.0, float(weight)))

        return GraphRelationship(
            relation_type=rel_type,
            source_id=agent1.id,
            target_id=agent2.id,
            weight=weight,
            properties={"context": rel_data.get("context", "")},
        )

    async def enhance_profile(
        self,
        agent_node: AgentNode,
        additional_context: str = "",
    ) -> AgentNode:
        """Enhance an existing agent profile with more detail.

        Args:
            agent_node: Existing agent node
            additional_context: Additional context for enhancement

        Returns:
            Enhanced AgentNode with deeper background
        """
        # This could be extended to add more detail to existing profiles
        logger.info("Enhancing profile for agent: %s", agent_node.name)
        return agent_node
