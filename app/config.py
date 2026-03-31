"""Application configuration via pydantic-settings.

All configuration is loaded from environment variables or a .env file.
Validated at startup to fail fast on misconfiguration.
"""

from enum import StrEnum
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.observability.config import ObservabilitySettings


class AppEnvironment(StrEnum):
    """Application deployment environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class AppSettings(BaseSettings):
    """Core application settings."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    app_name: str = Field(default="GraphSearchNeo4j")
    app_env: AppEnvironment = Field(default=AppEnvironment.DEVELOPMENT)
    app_debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    domain_auto_bootstrap: bool = Field(
        default=True,
        description="When true, ensure an active Domain exists at startup and via GET /domains/active.",
    )
    default_domain_key: str = Field(default="default", min_length=1, max_length=128)
    default_domain_name: str = Field(default="默认领域", min_length=1, max_length=256)


class Neo4jSettings(BaseSettings):
    """Neo4j connection and pool configuration."""

    model_config = SettingsConfigDict(env_prefix="NEO4J_", env_file=".env", extra="ignore")

    uri: str = Field(default="bolt://localhost:7687")
    username: str = Field(default="neo4j")
    password: str = Field(default="")
    database: str = Field(default="neo4j")

    @field_validator("uri")
    @classmethod
    def validate_uri_scheme(cls, v: str) -> str:
        allowed = ("bolt://", "bolt+s://", "neo4j://", "neo4j+s://")
        if not v.startswith(allowed):
            msg = f"Neo4j URI must start with one of {allowed}, got: {v}"
            raise ValueError(msg)
        return v


class OpenAISettings(BaseSettings):
    """OpenAI / compatible LLM API configuration."""

    model_config = SettingsConfigDict(env_prefix="OPENAI_", env_file=".env", extra="ignore")

    api_key: str = Field(default="")
    base_url: str = Field(default="https://api.openai.com/v1")
    model: str = Field(default="gpt-4o")


class EmbeddingSettings(BaseSettings):
    """Local embedding model configuration."""

    model_config = SettingsConfigDict(env_prefix="EMBEDDING_", env_file=".env", extra="ignore")

    model_path: str = Field(default="./model_files/embeddingmodel/m3e-large")
    dimension: int = Field(default=1024, ge=1)
    device: str = Field(default="cpu")

    @field_validator("model_path")
    @classmethod
    def validate_model_path(cls, v: str) -> str:
        path = Path(v)
        if not path.exists():
            # Soft warning — model may be mounted at runtime (Docker)
            import warnings

            warnings.warn(
                f"Embedding model path does not exist: {path.resolve()}. "
                "Ensure it is available before calling the embedding service.",
                stacklevel=2,
            )
        return v


class RetrievalSettings(BaseSettings):
    """Retrieval engine tuning parameters."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    vector_top_k: int = Field(default=10, ge=1, le=100)
    graph_traversal_depth: int = Field(default=2, ge=1, le=5)


class ExtractionSettings(BaseSettings):
    """Extraction pipeline configuration."""

    model_config = SettingsConfigDict(env_prefix="EXTRACTION_", env_file=".env", extra="ignore")

    max_concurrency: int = Field(default=5, ge=1, le=50)
    max_retries: int = Field(default=2, ge=0, le=5)
    chunk_size: int = Field(default=512, ge=64)
    chunk_overlap: int = Field(default=64, ge=0)


class RetrySettings(BaseSettings):
    """Retry configuration for database operations."""

    model_config = SettingsConfigDict(env_prefix="RETRY_", env_file=".env", extra="ignore")

    max_attempts: int = Field(default=3, ge=1, le=10)
    timeout: float = Field(default=30.0, ge=1.0, le=300.0)
    retry_delay: float = Field(default=1.0, ge=0.1, le=10.0)
    backoff_factor: float = Field(default=2.0, ge=1.0, le=5.0)


class SimulationSettings(BaseSettings):
    """Social simulation configuration."""

    model_config = SettingsConfigDict(env_prefix="SIMULATION_", env_file=".env", extra="ignore")

    max_agents: int = Field(default=50, ge=1, le=500)
    memory_decay_rate: float = Field(default=0.1, ge=0.0, le=1.0)
    interaction_probability: float = Field(default=0.3, ge=0.0, le=1.0)
    platform_sync_interval: int = Field(default=60, ge=10, le=3600)
    simulation_speed: float = Field(default=1.0, ge=0.1, le=100.0)
    enable_emotion: bool = Field(default=True)
    enable_memory_formation: bool = Field(default=True)
    enable_relationship_evolution: bool = Field(default=True)


class Settings(BaseSettings):
    """Aggregated application settings — single source of truth."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app: AppSettings = Field(default_factory=AppSettings)
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    extraction: ExtractionSettings = Field(default_factory=ExtractionSettings)
    retry: RetrySettings = Field(default_factory=RetrySettings)
    simulation: SimulationSettings = Field(default_factory=SimulationSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)


def get_settings() -> Settings:
    """Factory function for settings — facilitates DI and testing."""
    return Settings()
