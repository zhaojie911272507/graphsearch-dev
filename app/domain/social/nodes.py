"""Social simulation node domain models.

Extends the base node types with social simulation specific nodes:
- AgentNode: Simulated individual with profile, personality, and goals
- MemoryNode: Individual or collective memory with emotion tags
- WorldStateNode: Simulation world state at a point in time
- SimulationSessionNode: A simulation session with parameters and metrics
- SeedNode: Reality seed extracted from external sources
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import EntityType, NodeType
from app.domain.nodes import BaseNode, NodeMetadata
from app.domain.social.enums import (
    AgentState,
    EmotionType,
    MemoryType,
    PlatformType,
    SeedSourceType,
    SimulationStatus,
)


class AgentProfile(BaseModel):
    """Detailed profile information for a simulation agent."""

    model_config = ConfigDict(frozen=True)

    display_name: str = Field(default="", description="Display name on platform")
    avatar_description: str = Field(default="", description="Text description of avatar image")
    bio: str = Field(default="", description="Short bio/description")
    location: str = Field(default="", description="Geographic location")
    occupation: str = Field(default="", description="Job/role")
    interests: list[str] = Field(default_factory=list, description="List of interests/hobbies")
    social_class: str = Field(default="", description="Socioeconomic class indicator")
    education_level: str = Field(default="", description="Highest education level")
    relationship_status: str = Field(default="", description="Single/married/etc")
    political_leaning: str = Field(default="", description="Political orientation if applicable")
    values: list[str] = Field(default_factory=list, description="Core personal values")


class PersonalityTraits(BaseModel):
    """Big Five personality traits for agents."""

    model_config = ConfigDict(frozen=True)

    openness: float = Field(default=0.5, ge=0.0, le=1.0, description="Openness to experience")
    conscientiousness: float = Field(default=0.5, ge=0.0, le=1.0, description="Conscientiousness")
    extraversion: float = Field(default=0.5, ge=0.0, le=1.0, description="Extraversion")
    agreeableness: float = Field(default=0.5, ge=0.0, le=1.0, description="Agreeableness")
    neuroticism: float = Field(default=0.5, ge=0.0, le=1.0, description="Neuroticism")


class AgentNode(BaseNode):
    """Represents a simulated individual in the social world.

    Attributes:
        name: Agent's name
        profile: Detailed profile information
        background_story: Agent's life story and background
        personality: Big Five personality traits
        goals: Current active goals
        state: Current activity state
        platform: Primary platform for this agent
        metadata: Extended simulation metadata
    """

    model_config = ConfigDict(frozen=True)

    node_type: NodeType = Field(default=NodeType.ENTITY, frozen=True)
    name: str = Field(..., min_length=1, max_length=300)
    entity_type: EntityType = Field(default=EntityType.PERSON, frozen=True)
    description: str = Field(default="")

    # Agent-specific fields
    profile: AgentProfile = Field(default_factory=AgentProfile)
    background_story: str = Field(default="", description="Agent's background story")
    personality: PersonalityTraits = Field(default_factory=PersonalityTraits)
    goals: list[str] = Field(default_factory=list, description="Current active goals")
    state: AgentState = Field(default=AgentState.IDLE)
    platform: PlatformType = Field(default=PlatformType.WECHAT)

    # References to related nodes
    memory_ids: list[UUID] = Field(default_factory=list, description="Associated memory IDs")
    group_ids: list[UUID] = Field(default_factory=list, description="Associated group/community IDs")
    seed_id: UUID | None = Field(default=None, description="Source seed that generated this agent")

    def neo4j_properties(self) -> dict[str, object]:
        """Serialize to flat dict for Neo4j."""
        props = super().neo4j_properties()
        props.update(
            {
                "name": self.name,
                "entity_type": self.entity_type.value,
                "description": self.description,
                "profile": self.profile.model_dump_json(),
                "background_story": self.background_story,
                "personality": self.personality.model_dump_json(),
                "goals": self.goals,
                "state": self.state.value,
                "platform": self.platform.value,
                "memory_ids": [str(m) for m in self.memory_ids],
                "group_ids": [str(g) for g in self.group_ids],
                "seed_id": str(self.seed_id) if self.seed_id else None,
            }
        )
        return props


class MemoryNode(BaseNode):
    """Represents an individual or collective memory.

    Attributes:
        content: The memory content/text
        memory_type: Type of memory (individual/collective/episodic/semantic)
        timestamp: When the memory was formed
        importance: Importance score (0-1)
        emotion_tags: Associated emotions
        associated_agent_ids: Agents connected to this memory
        embedding: Vector embedding for semantic search
    """

    model_config = ConfigDict(frozen=True)

    node_type: NodeType = Field(default=NodeType.CONCEPT, frozen=True)
    name: str = Field(..., min_length=1, max_length=500, description="Memory title/summary")
    definition: str = Field(default="", description="Memory content")

    # Memory-specific fields
    content: str = Field(..., min_length=1, description="Full memory content")
    memory_type: MemoryType = Field(default=MemoryType.EPISODIC)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    emotion_tags: list[EmotionType] = Field(default_factory=list)
    associated_agent_ids: list[UUID] = Field(default_factory=list)
    embedding: tuple[float, ...] = Field(default=(), description="Vector embedding")

    @field_validator("embedding")
    @classmethod
    def validate_embedding_dimension(cls, v: tuple[float, ...]) -> tuple[float, ...]:
        """Enforce 1024 dimension for embeddings."""
        if len(v) > 0 and len(v) != 1024:
            msg = f"Embedding dimension must be 1024, got {len(v)}"
            raise ValueError(msg)
        return v

    def neo4j_properties(self) -> dict[str, object]:
        """Serialize to flat dict for Neo4j."""
        props = super().neo4j_properties()
        props.update(
            {
                "name": self.name,
                "definition": self.definition,
                "content": self.content,
                "memory_type": self.memory_type.value,
                "timestamp": self.timestamp.isoformat(),
                "importance": self.importance,
                "emotion_tags": [e.value for e in self.emotion_tags],
                "associated_agent_ids": [str(a) for a in self.associated_agent_ids],
                "embedding": list(self.embedding) if self.embedding else [],
            }
        )
        return props


class WorldStateNode(BaseNode):
    """Represents the state of the simulation world at a point in time.

    Attributes:
        world_key: Unique identifier for this world state
        platform: Which platform this state belongs to
        state_data: Arbitrary state data as JSON
        active_agent_ids: Currently active agents
        simulation_session_id: Parent simulation session
    """

    model_config = ConfigDict(frozen=True)

    node_type: NodeType = Field(default=NodeType.CONCEPT, frozen=True)
    name: str = Field(..., min_length=1, max_length=300, description="World state name")
    definition: str = Field(default="", description="World state description")

    # World-specific fields
    world_key: str = Field(..., min_length=1, max_length=128)
    platform: PlatformType = Field(default=PlatformType.WECHAT)
    state_data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    active_agent_ids: list[UUID] = Field(default_factory=list)
    simulation_session_id: UUID | None = Field(default=None)

    def neo4j_properties(self) -> dict[str, object]:
        """Serialize to flat dict for Neo4j."""
        props = super().neo4j_properties()
        props.update(
            {
                "name": self.name,
                "definition": self.definition,
                "world_key": self.world_key,
                "platform": self.platform.value,
                "state_data": self.state_data,  # Neo4j can store JSON
                "timestamp": self.timestamp.isoformat(),
                "active_agent_ids": [str(a) for a in self.active_agent_ids],
                "simulation_session_id": str(self.simulation_session_id)
                if self.simulation_session_id
                else None,
            }
        )
        return props


class SimulationSessionNode(BaseNode):
    """Represents a simulation session with configuration and metrics.

    Attributes:
        session_id: Unique session identifier
        status: Current session status
        parameters: Simulation parameters
        metrics: Performance and outcome metrics
        world_ids: Associated world states
        agent_ids: Participating agents
    """

    model_config = ConfigDict(frozen=True)

    node_type: NodeType = Field(default=NodeType.CONCEPT, frozen=True)
    name: str = Field(..., min_length=1, max_length=300, description="Session name")
    definition: str = Field(default="", description="Session description")

    # Session-specific fields
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    status: SimulationStatus = Field(default=SimulationStatus.INITIALIZING)
    start_time: datetime | None = Field(default=None)
    end_time: datetime | None = Field(default=None)
    parameters: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    world_ids: list[UUID] = Field(default_factory=list)
    agent_ids: list[UUID] = Field(default_factory=list)
    seed_ids: list[UUID] = Field(default_factory=list)

    def neo4j_properties(self) -> dict[str, object]:
        """Serialize to flat dict for Neo4j."""
        props = super().neo4j_properties()
        props.update(
            {
                "name": self.name,
                "definition": self.definition,
                "session_id": self.session_id,
                "status": self.status.value,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "parameters": self.parameters,
                "metrics": self.metrics,
                "world_ids": [str(w) for w in self.world_ids],
                "agent_ids": [str(a) for a in self.agent_ids],
                "seed_ids": [str(s) for s in self.seed_ids],
            }
        )
        return props


class SeedNode(BaseNode):
    """Represents a reality seed extracted from external sources.

    Attributes:
        source_url: Original source URL if applicable
        source_type: Type of source (URL/document/text/etc)
        raw_content: Original unprocessed content
        extracted_at: When this seed was extracted
        credibility_score: Source credibility (0-1)
        extracted_entity_ids: Entities extracted from this seed
        extracted_agent_ids: Agents generated from this seed
    """

    model_config = ConfigDict(frozen=True)

    node_type: NodeType = Field(default=NodeType.DOCUMENT, frozen=True)
    title: str = Field(..., min_length=1, max_length=500)
    source_url: str = Field(default="")
    content_hash: str = Field(default="")
    filename: str = Field(default="")
    file_size: int = Field(default=0)
    file_type: str = Field(default="")
    upload_status: str = Field(default="complete")
    parse_error: str | None = Field(default=None)

    # Seed-specific fields
    source_type: SeedSourceType = Field(default=SeedSourceType.TEXT)
    raw_content: str = Field(default="")
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    credibility_score: float = Field(default=0.5, ge=0.0, le=1.0)
    extracted_entity_ids: list[UUID] = Field(default_factory=list)
    extracted_agent_ids: list[UUID] = Field(default_factory=list)

    def neo4j_properties(self) -> dict[str, object]:
        """Serialize to flat dict for Neo4j."""
        props = super().neo4j_properties()
        props.update(
            {
                "title": self.title,
                "source_url": self.source_url,
                "content_hash": self.content_hash,
                "filename": self.filename,
                "file_size": self.file_size,
                "file_type": self.file_type,
                "upload_status": self.upload_status,
                "parse_error": self.parse_error,
                "source_type": self.source_type.value,
                "raw_content": self.raw_content,
                "extracted_at": self.extracted_at.isoformat(),
                "credibility_score": self.credibility_score,
                "extracted_entity_ids": [str(e) for e in self.extracted_entity_ids],
                "extracted_agent_ids": [str(a) for a in self.extracted_agent_ids],
            }
        )
        return props


class InteractionNode(BaseNode):
    """Represents an interaction between agents."""

    model_config = ConfigDict(frozen=True)

    node_type: NodeType = Field(default=NodeType.CONCEPT, frozen=True)
    name: str = Field(..., min_length=1, max_length=500, description="Interaction name")
    definition: str = Field(default="", description="Interaction description")

    # Interaction-specific fields
    interaction_type: str = Field(..., description="Type of interaction (POST, COMMENT, etc)")
    content: str = Field(default="", description="Interaction content")
    sender_id: UUID = Field(..., description="ID of the agent who sent the interaction")
    receiver_id: UUID | None = Field(default=None, description="ID of the receiving agent if any")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    interaction_metadata: dict = Field(default_factory=dict, alias="metadata", description="Additional interaction metadata")

    def neo4j_properties(self) -> dict[str, object]:
        """Serialize to flat dict for Neo4j."""
        props = super().neo4j_properties()
        props.update(
            {
                "name": self.name,
                "definition": self.definition,
                "interaction_type": self.interaction_type,
                "content": self.content,
                "sender_id": str(self.sender_id),
                "receiver_id": str(self.receiver_id) if self.receiver_id else None,
                "timestamp": self.timestamp.isoformat(),
                "metadata": self.interaction_metadata,
            }
        )
        return props


class ReportNode(BaseNode):
    """Represents a generated analysis report."""

    model_config = ConfigDict(frozen=True)

    node_type: NodeType = Field(default=NodeType.CONCEPT, frozen=True)
    name: str = Field(..., min_length=1, max_length=500, description="Report name")
    definition: str = Field(default="", description="Report description")

    # Report-specific fields
    report_type: str = Field(..., description="Type of report")
    session_id: UUID = Field(..., description="Associated simulation session ID")
    content: dict = Field(default_factory=dict, description="Report content data")
    summary: str = Field(default="", description="Natural language summary")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    time_range_start: datetime | None = Field(default=None)
    time_range_end: datetime | None = Field(default=None)

    def neo4j_properties(self) -> dict[str, object]:
        """Serialize to flat dict for Neo4j."""
        props = super().neo4j_properties()
        props.update(
            {
                "name": self.name,
                "definition": self.definition,
                "report_type": self.report_type,
                "session_id": str(self.session_id),
                "content": self.content,
                "summary": self.summary,
                "generated_at": self.generated_at.isoformat(),
                "time_range_start": self.time_range_start.isoformat() if self.time_range_start else None,
                "time_range_end": self.time_range_end.isoformat() if self.time_range_end else None,
            }
        )
        return props
