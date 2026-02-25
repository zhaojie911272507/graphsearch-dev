"""Tests for evaluation metrics aggregation and delta computation."""

import pytest

from app.evaluation.metrics import (
    aggregate_results,
    compute_deltas,
    compute_latency_stats,
)
from app.evaluation.schemas import (
    LatencyBreakdown,
    RagasScores,
    RetrievalMode,
    SingleQueryResult,
)


class TestLatencyStats:
    def test_basic_stats(self) -> None:
        stats = compute_latency_stats([10.0, 20.0, 30.0, 40.0, 50.0])
        assert stats.min_ms == 10.0
        assert stats.max_ms == 50.0
        assert stats.mean_ms == 30.0
        assert stats.p50_ms == 30.0

    def test_empty(self) -> None:
        stats = compute_latency_stats([])
        assert stats.mean_ms == 0.0

    def test_single_value(self) -> None:
        stats = compute_latency_stats([42.0])
        assert stats.p50_ms == 42.0
        assert stats.p99_ms == 42.0
        assert stats.mean_ms == 42.0


def _make_result(
    mode: RetrievalMode,
    precision: float = 0.5,
    recall: float = 0.8,
    faithfulness: float = 0.9,
    relevance: float = 0.85,
    retrieval_ms: float = 100.0,
    e2e_ms: float = 200.0,
) -> SingleQueryResult:
    return SingleQueryResult(
        question="test question",
        mode=mode,
        generated_answer="test answer",
        expected_answer="expected answer",
        latency=LatencyBreakdown(
            total_retrieval_ms=retrieval_ms,
            total_e2e_ms=e2e_ms,
        ),
        ragas_scores=RagasScores(
            context_precision=precision,
            context_recall=recall,
            faithfulness=faithfulness,
            answer_relevance=relevance,
        ),
    )


class TestAggregateResults:
    def test_aggregate_single_mode(self) -> None:
        results = [
            _make_result(RetrievalMode.VECTOR_ONLY, precision=0.4),
            _make_result(RetrievalMode.VECTOR_ONLY, precision=0.6),
        ]
        agg = aggregate_results(results, RetrievalMode.VECTOR_ONLY)
        assert agg.num_queries == 2
        assert agg.avg_context_precision == 0.5

    def test_aggregate_filters_mode(self) -> None:
        results = [
            _make_result(RetrievalMode.VECTOR_ONLY),
            _make_result(RetrievalMode.HYBRID),
        ]
        agg = aggregate_results(results, RetrievalMode.HYBRID)
        assert agg.num_queries == 1

    def test_aggregate_empty(self) -> None:
        agg = aggregate_results([], RetrievalMode.VECTOR_ONLY)
        assert agg.num_queries == 0

    def test_latency_aggregation(self) -> None:
        results = [
            _make_result(RetrievalMode.HYBRID, retrieval_ms=50.0, e2e_ms=150.0),
            _make_result(RetrievalMode.HYBRID, retrieval_ms=80.0, e2e_ms=250.0),
        ]
        agg = aggregate_results(results, RetrievalMode.HYBRID)
        assert agg.retrieval_latency.mean_ms == 65.0


class TestComputeDeltas:
    def test_positive_quality_delta(self) -> None:
        vo = [_make_result(RetrievalMode.VECTOR_ONLY, recall=0.5)]
        hy = [_make_result(RetrievalMode.HYBRID, recall=0.9)]
        vo_agg = aggregate_results(vo, RetrievalMode.VECTOR_ONLY)
        hy_agg = aggregate_results(hy, RetrievalMode.HYBRID)
        deltas = compute_deltas(vo_agg, hy_agg)

        recall_delta = next(d for d in deltas if d.metric_name == "context_recall")
        assert recall_delta.absolute_delta > 0
        assert recall_delta.relative_delta_pct > 0

    def test_latency_delta(self) -> None:
        vo = [_make_result(RetrievalMode.VECTOR_ONLY, retrieval_ms=50.0)]
        hy = [_make_result(RetrievalMode.HYBRID, retrieval_ms=85.0)]
        vo_agg = aggregate_results(vo, RetrievalMode.VECTOR_ONLY)
        hy_agg = aggregate_results(hy, RetrievalMode.HYBRID)
        deltas = compute_deltas(vo_agg, hy_agg)

        lat_delta = next(d for d in deltas if d.metric_name == "retrieval_latency_p50")
        assert lat_delta.absolute_delta > 0
        assert lat_delta.hybrid_value > lat_delta.vector_only_value

    def test_all_delta_metrics_present(self) -> None:
        vo = [_make_result(RetrievalMode.VECTOR_ONLY)]
        hy = [_make_result(RetrievalMode.HYBRID)]
        vo_agg = aggregate_results(vo, RetrievalMode.VECTOR_ONLY)
        hy_agg = aggregate_results(hy, RetrievalMode.HYBRID)
        deltas = compute_deltas(vo_agg, hy_agg)
        names = {d.metric_name for d in deltas}
        assert "context_precision" in names
        assert "context_recall" in names
        assert "faithfulness" in names
        assert "answer_relevance" in names
        assert "retrieval_latency_p50" in names
        assert "e2e_latency_p50" in names
