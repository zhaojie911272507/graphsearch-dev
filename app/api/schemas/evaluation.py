"""Pydantic schemas for evaluation and monitoring API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class EvaluationMetricSchema(BaseModel):
    """Single evaluation metric."""

    name: str = Field(..., description="Metric name (precision, recall, etc.)")
    value: float = Field(..., ge=0.0, le=1.0, description="Metric value")
    previous_value: float | None = Field(default=None, description="Previous period value")
    change: float | None = Field(default=None, description="Change from previous")
    trend: str = Field(default="stable", description="up, down, stable")
    target: float | None = Field(default=None, description="Target value")


class EvaluationMetricsResponseSchema(BaseModel):
    """Evaluation metrics response."""

    metrics: dict[str, EvaluationMetricSchema] = Field(default_factory=dict)
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    evaluated_queries: int = Field(default=0, description="Number of queries evaluated")
    evaluation_period: dict[str, datetime] = Field(
        default_factory=lambda: {"start": datetime.utcnow(), "end": datetime.utcnow()}
    )


class MetricTimeSeriesSchema(BaseModel):
    """Time series data for a metric."""

    metric_name: str
    data_points: list[dict[str, object]] = Field(
        default_factory=list,
        description="List of {timestamp, value} objects",
    )
    avg_value: float = 0.0
    min_value: float = 0.0
    max_value: float = 0.0


class EvaluationTrendResponseSchema(BaseModel):
    """Evaluation metrics trend over time."""

    start_date: datetime
    end_date: datetime
    granularity: str = Field(..., description="day, week, month")
    metrics: list[MetricTimeSeriesSchema] = Field(default_factory=list)


class AblationStudyResponseSchema(BaseModel):
    """A/B comparison between retrieval strategies."""

    vector_only: dict[str, EvaluationMetricSchema] = Field(
        default_factory=dict,
        description="Metrics for vector-only retrieval",
    )
    hybrid: dict[str, EvaluationMetricSchema] = Field(
        default_factory=dict,
        description="Metrics for hybrid (vector + graph) retrieval",
    )
    improvement: dict[str, float] = Field(
        default_factory=dict,
        description="Percentage improvement for each metric",
    )
    statistical_significance: dict[str, float] = Field(
        default_factory=dict,
        description="P-values for each metric comparison",
    )
    sample_size: int = Field(default=0, description="Number of test queries")


class QueryEvaluationSchema(BaseModel):
    """Evaluation result for a single query."""

    id: UUID
    query_text: str = Field(..., description="The query text")
    context_precision: float = 0.0
    context_recall: float = 0.0
    faithfulness: float = 0.0
    answer_relevance: float = 0.0
    latency_ms: float = 0.0
    retrieved_chunks: int = 0
    retrieved_entities: int = 0
    created_at: datetime


class PipelineConfigSchema(BaseModel):
    """RAG pipeline configuration."""

    version: str = Field(..., description="Configuration version")
    retrieval: dict[str, object] = Field(
        default_factory=dict,
        description="Retrieval settings",
    )
    generation: dict[str, object] = Field(
        default_factory=dict,
        description="Generation settings",
    )
    created_at: datetime
    created_by: str
    is_active: bool = False


class PipelineConfigCreateSchema(BaseModel):
    """Request to create a pipeline configuration."""

    version: str = Field(..., pattern=r"^v\d+\.\d+\.\d+$")
    retrieval: dict[str, object] = Field(default_factory=dict)
    generation: dict[str, object] = Field(default_factory=dict)
    change_summary: str = Field(default="", max_length=500)


class PipelineConfigListResponseSchema(BaseModel):
    """List of pipeline configurations."""

    configs: list[PipelineConfigSchema] = Field(default_factory=list)
    active_version: str | None = None


class PromptTemplateSchema(BaseModel):
    """Prompt template for extraction or generation."""

    id: UUID
    name: str = Field(..., description="Template name")
    template_type: str = Field(..., description="extraction, generation, rewriter")
    content: str = Field(..., description="Prompt template content")
    variables: list[str] = Field(default_factory=list, description="Template variables")
    version: str = Field(..., description="Version string")
    is_active: bool = False
    created_at: datetime
    updated_at: datetime
    created_by: str


class PromptTemplateCreateSchema(BaseModel):
    """Request to create a prompt template."""

    name: str = Field(..., max_length=100)
    template_type: str
    content: str
    variables: list[str] = Field(default_factory=list)
    version: str = "v1.0.0"


class PromptTestRequestSchema(BaseModel):
    """Request to test a prompt template."""

    template_id: UUID | None = None
    template_content: str | None = None
    variables: dict[str, str] = Field(default_factory=dict, description="Variable values for testing")
    test_input: str = Field(..., description="Test input text")


class PromptTestResponseSchema(BaseModel):
    """Response from prompt test."""

    rendered_prompt: str = Field(..., description="Rendered prompt with variables substituted")
    llm_response: str | None = Field(default=None, description="LLM response if executed")
    latency_ms: float = 0.0
    tokens_used: int = 0
