"""RAGAS-based evaluation metrics (PRD §9.1 / §9.2).

Wraps the RAGAS library for standardised RAG evaluation and adds
aggregate / delta computation for the ablation study.
"""

import logging
import statistics

from langchain_openai import ChatOpenAI
from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    Faithfulness,
    LLMContextPrecisionWithReference,
    LLMContextRecall,
    ResponseRelevancy,
)

from app.config import OpenAISettings
from app.evaluation.schemas import (
    AggregateMetrics,
    DeltaMetrics,
    LatencyStats,
    RagasScores,
    RetrievalMode,
    SingleQueryResult,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────
# RAGAS Evaluation
# ──────────────────────────────────────────


def build_ragas_llm(openai_settings: OpenAISettings) -> LangchainLLMWrapper:
    """Create a RAGAS-compatible evaluator LLM."""
    llm = ChatOpenAI(
        api_key=openai_settings.api_key,  # type: ignore[arg-type]
        base_url=openai_settings.base_url,
        model=openai_settings.model,
        temperature=0.0,
    )
    return LangchainLLMWrapper(llm)


async def compute_ragas_scores(
    question: str,
    generated_answer: str,
    retrieved_contexts: list[str],
    expected_answer: str,
    evaluator_llm: LangchainLLMWrapper,
) -> RagasScores:
    """Evaluate a single query result using RAGAS metrics.

    Metrics computed (PRD §9.2):
      - Context Precision (with reference)
      - Context Recall
      - Faithfulness
      - Answer Relevance
    """
    if not retrieved_contexts:
        return RagasScores()

    sample = SingleTurnSample(
        user_input=question,
        response=generated_answer,
        retrieved_contexts=retrieved_contexts,
        reference=expected_answer,
    )

    dataset = EvaluationDataset(samples=[sample])

    try:
        result = evaluate(
            dataset=dataset,
            metrics=[
                LLMContextPrecisionWithReference(),
                LLMContextRecall(),
                Faithfulness(),
                ResponseRelevancy(),
            ],
            llm=evaluator_llm,
        )

        scores = result.to_pandas().iloc[0]
        return RagasScores(
            context_precision=_safe_score(scores.get("context_precision")),
            context_recall=_safe_score(scores.get("context_recall")),
            faithfulness=_safe_score(scores.get("faithfulness")),
            answer_relevance=_safe_score(scores.get("answer_relevancy")),
        )
    except Exception as exc:
        logger.warning("RAGAS evaluation failed for query '%s': %s", question[:60], exc)
        return RagasScores()


def _safe_score(value: object) -> float:
    """Clamp to [0, 1], defaulting NaN/None to 0."""
    try:
        f = float(value)  # type: ignore[arg-type]
        if f != f:  # NaN check
            return 0.0
        return max(0.0, min(1.0, f))
    except (TypeError, ValueError):
        return 0.0


# ──────────────────────────────────────────
# Aggregation
# ──────────────────────────────────────────


def compute_latency_stats(values_ms: list[float]) -> LatencyStats:
    """Compute percentile-based latency statistics."""
    if not values_ms:
        return LatencyStats()

    sorted_v = sorted(values_ms)
    n = len(sorted_v)

    def _percentile(pct: float) -> float:
        idx = int(pct / 100.0 * (n - 1))
        return sorted_v[min(idx, n - 1)]

    return LatencyStats(
        p50_ms=round(_percentile(50), 2),
        p90_ms=round(_percentile(90), 2),
        p95_ms=round(_percentile(95), 2),
        p99_ms=round(_percentile(99), 2),
        mean_ms=round(statistics.mean(sorted_v), 2),
        min_ms=round(sorted_v[0], 2),
        max_ms=round(sorted_v[-1], 2),
    )


def aggregate_results(
    results: list[SingleQueryResult],
    mode: RetrievalMode,
) -> AggregateMetrics:
    """Aggregate per-query RAGAS results into summary metrics."""
    mode_results = [r for r in results if r.mode == mode]
    n = len(mode_results)
    if n == 0:
        return AggregateMetrics(mode=mode)

    def _avg(extractor) -> float:  # type: ignore[no-untyped-def]
        return round(statistics.mean(extractor(r) for r in mode_results), 4)

    retrieval_latencies = [r.latency.total_retrieval_ms for r in mode_results]
    e2e_latencies = [r.latency.total_e2e_ms for r in mode_results]

    return AggregateMetrics(
        mode=mode,
        num_queries=n,
        avg_context_precision=_avg(lambda r: r.ragas_scores.context_precision),
        avg_context_recall=_avg(lambda r: r.ragas_scores.context_recall),
        avg_faithfulness=_avg(lambda r: r.ragas_scores.faithfulness),
        avg_answer_relevance=_avg(lambda r: r.ragas_scores.answer_relevance),
        retrieval_latency=compute_latency_stats(retrieval_latencies),
        e2e_latency=compute_latency_stats(e2e_latencies),
    )


def compute_deltas(
    vector_only: AggregateMetrics,
    hybrid: AggregateMetrics,
) -> list[DeltaMetrics]:
    """Compute absolute and relative differences for the ablation study (PRD §9.2)."""
    pairs = [
        ("context_precision", vector_only.avg_context_precision, hybrid.avg_context_precision),
        ("context_recall", vector_only.avg_context_recall, hybrid.avg_context_recall),
        ("faithfulness", vector_only.avg_faithfulness, hybrid.avg_faithfulness),
        ("answer_relevance", vector_only.avg_answer_relevance, hybrid.avg_answer_relevance),
        ("retrieval_latency_p50", vector_only.retrieval_latency.p50_ms, hybrid.retrieval_latency.p50_ms),
        ("retrieval_latency_p95", vector_only.retrieval_latency.p95_ms, hybrid.retrieval_latency.p95_ms),
        ("e2e_latency_p50", vector_only.e2e_latency.p50_ms, hybrid.e2e_latency.p50_ms),
        ("e2e_latency_p95", vector_only.e2e_latency.p95_ms, hybrid.e2e_latency.p95_ms),
    ]

    deltas: list[DeltaMetrics] = []
    for name, vo_val, hy_val in pairs:
        abs_delta = round(hy_val - vo_val, 4)
        rel_pct = round((abs_delta / vo_val) * 100, 2) if vo_val != 0 else 0.0
        deltas.append(
            DeltaMetrics(
                metric_name=name,
                vector_only_value=round(vo_val, 4),
                hybrid_value=round(hy_val, 4),
                absolute_delta=abs_delta,
                relative_delta_pct=rel_pct,
            )
        )

    return deltas
