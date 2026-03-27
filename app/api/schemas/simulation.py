"""Simulation API schemas.

Pydantic schemas for request/response validation in the simulation API.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.social.enums import ReportType


# ──────────────────────────────────────────
# Seed Extraction Schemas
# ──────────────────────────────────────────


class SeedExtractRequest(BaseModel):
    """Request to extract a reality seed."""

    source_url: str | None = Field(default=None, description="URL source if applicable")
    source_type: str = Field(default="TEXT", description="TEXT|URL|DOCUMENT|IMAGE|VIDEO|AUDIO")
    raw_content: str = Field(default="", description="Raw text content")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SeedExtractResponse(BaseModel):
    """Response from seed extraction."""

    seed_id: UUID
    source_url: str
    source_type: str
    extracted_at: datetime
    credibility_score: float
    extracted_entity_count: int
    extracted_agent_count: int
    status: str = "success"


# ──────────────────────────────────────────
# Agent Generation Schemas
# ──────────────────────────────────────────


class PersonalityTraitsSchema(BaseModel):
    """Big Five personality traits."""

    openness: float = Field(default=0.5, ge=0.0, le=1.0)
    conscientiousness: float = Field(default=0.5, ge=0.0, le=1.0)
    extraversion: float = Field(default=0.5, ge=0.0, le=1.0)
    agreeableness: float = Field(default=0.5, ge=0.0, le=1.0)
    neuroticism: float = Field(default=0.5, ge=0.0, le=1.0)


class AgentProfileSchema(BaseModel):
    """Agent profile information."""

    display_name: str = Field(default="")
    avatar_description: str = Field(default="")
    bio: str = Field(default="")
    location: str = Field(default="")
    occupation: str = Field(default="")
    interests: list[str] = Field(default_factory=list)
    social_class: str = Field(default="")
    education_level: str = Field(default="")
    relationship_status: str = Field(default="")
    values: list[str] = Field(default_factory=list)


class AgentGenerateRequest(BaseModel):
    """Request to generate agents from seed data."""

    seed_ids: list[UUID] = Field(default_factory=list, description="Source seeds")
    profile_count: int = Field(default=5, ge=1, le=100, description="Number of agents to generate")
    platform: str = Field(default="WECHAT", description="WECHAT|XIAOHONGSHU")
    custom_traits: dict[str, Any] = Field(default_factory=dict, description="Custom trait constraints")


class AgentSchema(BaseModel):
    """Agent information response."""

    id: UUID
    name: str
    platform: str
    state: str
    profile: AgentProfileSchema
    personality: PersonalityTraitsSchema
    background_story: str
    goals: list[str]
    memory_count: int = 0
    created_at: datetime


class AgentGenerateResponse(BaseModel):
    """Response from agent generation."""

    agents: list[AgentSchema]
    seed_ids: list[UUID]
    generation_timestamp: datetime
    status: str = "success"


# ──────────────────────────────────────────
# World Configuration Schemas
# ──────────────────────────────────────────


class PlatformConfigSchema(BaseModel):
    """Platform-specific configuration."""

    platform: str = Field(..., description="WECHAT|XIAOHONGSHU")
    post_frequency_range: tuple[float, float] = Field(default=(0.1, 2.0))
    interaction_probability: float = Field(default=0.3)
    content_topics: list[str] = Field(default_factory=list)
    trending_hashtags: list[str] = Field(default_factory=list)
    community_rules: list[str] = Field(default_factory=list)


class WorldConfigRequest(BaseModel):
    """Request to configure simulation world."""

    world_key: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=300)
    description: str = Field(default="")
    platform: str = Field(default="WECHAT")
    state_data: dict[str, Any] = Field(default_factory=dict)
    platform_config: PlatformConfigSchema | None = Field(default=None)


class WorldConfigResponse(BaseModel):
    """Response from world configuration."""

    world_id: UUID
    world_key: str
    name: str
    platform: str
    timestamp: datetime
    status: str = "success"


# ──────────────────────────────────────────
# Simulation Bootstrap Schemas
# ──────────────────────────────────────────


class SimulationParamsSchema(BaseModel):
    """Simulation parameters."""

    max_agents: int = Field(default=50, ge=1, le=500)
    memory_decay_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    interaction_probability: float = Field(default=0.3, ge=0.0, le=1.0)
    platform_sync_interval: int = Field(default=60, ge=10, le=3600)
    simulation_speed: float = Field(default=1.0, ge=0.1, le=100.0)
    enable_emotion: bool = Field(default=True)
    enable_memory_formation: bool = Field(default=True)
    enable_relationship_evolution: bool = Field(default=True)


class SimulationBootstrapRequest(BaseModel):
    """Request to bootstrap a full simulation."""

    name: str = Field(..., min_length=1, max_length=300)
    description: str = Field(default="")
    seed_sources: list[dict[str, str]] = Field(
        default_factory=list, description="List of {source_type, content/url}"
    )
    agent_count: int = Field(default=10, ge=1, le=100)
    platforms: list[str] = Field(default=["WECHAT"], description="WECHAT|XIAOHONGSHU")
    parameters: SimulationParamsSchema = Field(default_factory=SimulationParamsSchema)


class SimulationSessionSchema(BaseModel):
    """Simulation session information."""

    id: UUID
    session_id: str
    name: str
    status: str
    start_time: datetime | None
    end_time: datetime | None
    agent_count: int
    world_count: int
    parameters: dict[str, Any]


class SimulationBootstrapResponse(BaseModel):
    """Response from simulation bootstrap."""

    session: SimulationSessionSchema
    agents_created: int
    worlds_created: int
    seeds_processed: int
    status: str = "success"
    message: str = ""


# ──────────────────────────────────────────
# Memory Management Schemas
# ──────────────────────────────────────────


class MemoryCreateRequest(BaseModel):
    """Request to create a memory for an agent."""

    agent_id: UUID
    content: str = Field(..., min_length=1)
    memory_type: str = Field(default="EPISODIC")
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    emotion_tags: list[str] = Field(default_factory=list)


class MemorySchema(BaseModel):
    """Memory information."""

    id: UUID
    name: str
    content: str
    memory_type: str
    timestamp: datetime
    importance: float
    emotion_tags: list[str]
    associated_agent_ids: list[UUID]


# ──────────────────────────────────────────
# Query Schemas
# ──────────────────────────────────────────


class SimulationQueryRequest(BaseModel):
    """Request to query simulation state."""

    session_id: UUID | None = Field(default=None)
    agent_id: UUID | None = Field(default=None)
    world_id: UUID | None = Field(default=None)
    query_type: str = Field(default="STATUS", description="STATUS|AGENTS|MEMORIES|WORLDS")
    filters: dict[str, Any] = Field(default_factory=dict)


class SimulationQueryResponse(BaseModel):
    """Response from simulation query."""

    data: Any
    count: int = 0
    timestamp: datetime
