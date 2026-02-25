"""Tests for evaluation report generation (PRD §9.4)."""

import json
from pathlib import Path

import pytest

from app.evaluation.report import print_report, save_report_json
from app.evaluation.schemas import (
    AggregateMetrics,
    DeltaMetrics,
    EvaluationReport,
    LatencyStats,
    RetrievalMode,
)


@pytest.fixture
def sample_report() -> EvaluationReport:
    """Create a representative ablation study report."""
    vo = AggregateMetrics(
        mode=RetrievalMode.VECTOR_ONLY,
        num_queries=5,
        avg_context_precision=0.45,
        avg_context_recall=0.50,
        avg_faithfulness=0.60,
        avg_answer_relevance=0.55,
        retrieval_latency=LatencyStats(
            p50_ms=50.0, p90_ms=80.0, p95_ms=90.0, p99_ms=100.0,
            mean_ms=55.0, min_ms=30.0, max_ms=110.0,
        ),
        e2e_latency=LatencyStats(
            p50_ms=200.0, p90_ms=350.0, p95_ms=400.0, p99_ms=450.0,
            mean_ms=220.0, min_ms=150.0, max_ms=500.0,
        ),
    )
    hy = AggregateMetrics(
        mode=RetrievalMode.HYBRID,
        num_queries=5,
        avg_context_precision=0.65,
        avg_context_recall=0.85,
        avg_faithfulness=0.88,
        avg_answer_relevance=0.82,
        retrieval_latency=LatencyStats(
            p50_ms=85.0, p90_ms=130.0, p95_ms=150.0, p99_ms=170.0,
            mean_ms=90.0, min_ms=50.0, max_ms=180.0,
        ),
        e2e_latency=LatencyStats(
            p50_ms=280.0, p90_ms=420.0, p95_ms=480.0, p99_ms=520.0,
            mean_ms=300.0, min_ms=200.0, max_ms=550.0,
        ),
    )
    deltas = [
        DeltaMetrics(
            metric_name="context_recall",
            vector_only_value=0.50, hybrid_value=0.85,
            absolute_delta=0.35, relative_delta_pct=70.0,
        ),
        DeltaMetrics(
            metric_name="faithfulness",
            vector_only_value=0.60, hybrid_value=0.88,
            absolute_delta=0.28, relative_delta_pct=46.67,
        ),
        DeltaMetrics(
            metric_name="answer_relevance",
            vector_only_value=0.55, hybrid_value=0.82,
            absolute_delta=0.27, relative_delta_pct=49.09,
        ),
        DeltaMetrics(
            metric_name="retrieval_latency_p50",
            vector_only_value=50.0, hybrid_value=85.0,
            absolute_delta=35.0, relative_delta_pct=70.0,
        ),
    ]
    return EvaluationReport(
        dataset_name="test_dataset",
        vector_only=vo,
        hybrid=hy,
        deltas=deltas,
    )


class TestPrintReport:
    def test_prints_ablation_header(
        self, sample_report: EvaluationReport, capsys: pytest.CaptureFixture[str]
    ) -> None:
        print_report(sample_report)
        captured = capsys.readouterr()
        assert "ABLATION STUDY REPORT" in captured.out
        assert "test_dataset" in captured.out
        assert "GRAPH LIFT VERDICT" in captured.out

    def test_verdict_shows_justified(
        self, sample_report: EvaluationReport, capsys: pytest.CaptureFixture[str]
    ) -> None:
        print_report(sample_report)
        captured = capsys.readouterr()
        assert "JUSTIFIED" in captured.out


class TestSaveReportJson:
    def test_saves_valid_json(
        self, sample_report: EvaluationReport, tmp_path: Path
    ) -> None:
        result_path = save_report_json(sample_report, output_dir=tmp_path)
        assert result_path.exists()
        assert result_path.suffix == ".json"

        data = json.loads(result_path.read_text(encoding="utf-8"))
        assert data["dataset_name"] == "test_dataset"
        assert data["vector_only"]["num_queries"] == 5
        assert data["hybrid"]["avg_context_recall"] == 0.85

    def test_creates_output_dir(
        self, sample_report: EvaluationReport, tmp_path: Path
    ) -> None:
        nested = tmp_path / "deep" / "nested"
        result_path = save_report_json(sample_report, output_dir=nested)
        assert result_path.exists()
        assert nested.exists()
