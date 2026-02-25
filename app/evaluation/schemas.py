"""Evaluation data models aligned with RAGAS framework.

Data structures follow the PRD §9.2 metric definitions and §9.3 golden
dataset format: [question, expected_answer, expected_contexts].
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RetrievalMode(StrEnum):
    """The two retrieval strategies for ablation study (PRD §9.2)."""

    VECTOR_ONLY = "vector_only"
    HYBRID = "hybrid"


# ──────────────────────────────────────────
# Golden Dataset (PRD §9.3)
# ──────────────────────────────────────────


class EvalCase(BaseModel):
    """A single evaluation case — mirrors PRD §9.3 data structure.

    Fields:
        question: The user query.
        expected_answer: Ground-truth reference answer.
        expected_contexts: Ground-truth context passages the retriever
            should find (used by RAGAS Context Recall).
        category: Question category for per-category breakdown.
        difficulty: Difficulty level for stratified analysis.
    """

    model_config = ConfigDict(frozen=True)

    question: str = Field(..., min_length=1)
    expected_answer: str = Field(..., min_length=1)
    expected_contexts: list[str] = Field(
        default_factory=list,
        description="Ground-truth context passages (text) required to answer the question.",
    )
    category: str = Field(default="general")
    difficulty: str = Field(default="medium")


class EvalDataset(BaseModel):
    """A collection of evaluation cases with metadata."""

    name: str = Field(default="golden_qa")
    description: str = Field(default="")
    cases: list[EvalCase] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ──────────────────────────────────────────
# Per-Query Results
# ──────────────────────────────────────────


class LatencyBreakdown(BaseModel):
    """Fine-grained latency measurement for a single query."""

    embedding_ms: float = Field(default=0.0, ge=0.0)
    vector_search_ms: float = Field(default=0.0, ge=0.0)
    graph_traversal_ms: float = Field(default=0.0, ge=0.0)
    llm_generation_ms: float = Field(default=0.0, ge=0.0)
    total_retrieval_ms: float = Field(default=0.0, ge=0.0)
    total_e2e_ms: float = Field(default=0.0, ge=0.0)


class RagasScores(BaseModel):
    """RAGAS metric scores for a single query (PRD §9.2)."""

    context_precision: float = Field(default=0.0, ge=0.0, le=1.0)
    context_recall: float = Field(default=0.0, ge=0.0, le=1.0)
    faithfulness: float = Field(default=0.0, ge=0.0, le=1.0)
    answer_relevance: float = Field(default=0.0, ge=0.0, le=1.0)


class SingleQueryResult(BaseModel):
    """Complete evaluation result for one query under one retrieval mode."""

    question: str
    mode: RetrievalMode
    generated_answer: str = Field(default="")
    expected_answer: str = Field(default="")
    retrieved_contexts: list[str] = Field(default_factory=list)
    expected_contexts: list[str] = Field(default_factory=list)
    retrieved_entity_names: list[str] = Field(default_factory=list)
    num_chunks: int = 0
    num_entities: int = 0
    num_relations: int = 0
    latency: LatencyBreakdown = Field(default_factory=LatencyBreakdown)
    ragas_scores: RagasScores = Field(default_factory=RagasScores)


# ──────────────────────────────────────────
# Aggregate Metrics
# ──────────────────────────────────────────


class LatencyStats(BaseModel):
    """Aggregate latency statistics."""

    p50_ms: float = 0.0
    p90_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    mean_ms: float = 0.0
    min_ms: float = 0.0
    max_ms: float = 0.0


class AggregateMetrics(BaseModel):
    """Aggregated RAGAS metrics for all queries under a single retrieval mode."""

    mode: RetrievalMode
    num_queries: int = 0

    avg_context_precision: float = 0.0
    avg_context_recall: float = 0.0
    avg_faithfulness: float = 0.0
    avg_answer_relevance: float = 0.0

    retrieval_latency: LatencyStats = Field(default_factory=LatencyStats)
    e2e_latency: LatencyStats = Field(default_factory=LatencyStats)


# ──────────────────────────────────────────
# Ablation / Delta (PRD §9.2 Graph Lift)
# ──────────────────────────────────────────


class DeltaMetrics(BaseModel):
    """Absolute and relative difference: hybrid - vector_only."""

    metric_name: str
    vector_only_value: float
    hybrid_value: float
    absolute_delta: float
    relative_delta_pct: float = Field(
        description="(hybrid - vector_only) / vector_only * 100"
    )


# ──────────────────────────────────────────
# Final Report
# ──────────────────────────────────────────


class EvaluationReport(BaseModel):
    """The final ablation study report (PRD §9.2 Graph Lift)."""

    dataset_name: str
    run_timestamp: datetime = Field(default_factory=datetime.utcnow)

    vector_only: AggregateMetrics
    hybrid: AggregateMetrics

    deltas: list[DeltaMetrics] = Field(default_factory=list)
    per_query_results: list[SingleQueryResult] = Field(default_factory=list)
