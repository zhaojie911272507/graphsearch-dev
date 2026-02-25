"""Evaluation report generation (PRD §9.4).

Output formats:
1. Console table with ablation study results.
2. JSON file for CI/CD pipelines and dashboards (MLflow / LangSmith / Grafana).
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from app.evaluation.schemas import (
    AggregateMetrics,
    DeltaMetrics,
    EvaluationReport,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────
# Console Report
# ──────────────────────────────────────────


def print_report(report: EvaluationReport) -> None:
    """Print the ablation study report to stdout."""
    vo = report.vector_only
    hy = report.hybrid

    sep = "=" * 82
    thin = "-" * 82

    print(f"\n{sep}")
    print(f"  ABLATION STUDY REPORT — Graph Lift Analysis (PRD §9.2)")
    print(f"  Dataset : {report.dataset_name}")
    print(f"  Time    : {report.run_timestamp.isoformat()}")
    print(f"  Queries : {vo.num_queries}")
    print(sep)

    # ── Retrieval Quality ──
    print(f"\n{'RETRIEVAL QUALITY (RAGAS)':^82}")
    print(thin)
    _print_metric_table(
        rows=[d for d in report.deltas if d.metric_name in {
            "context_precision", "context_recall"
        }],
    )

    # ── Generation Quality ──
    print(f"\n{'GENERATION QUALITY (RAGAS)':^82}")
    print(thin)
    _print_metric_table(
        rows=[d for d in report.deltas if d.metric_name in {
            "faithfulness", "answer_relevance"
        }],
    )

    # ── Latency ──
    print(f"\n{'LATENCY OVERHEAD':^82}")
    print(thin)
    _print_metric_table(
        rows=[d for d in report.deltas if "latency" in d.metric_name],
        unit="ms",
    )

    # ── Latency Breakdown ──
    print(f"\n{'LATENCY BREAKDOWN (ms)':^82}")
    print(thin)
    _print_latency_detail(vo, hy)

    # ── Verdict ──
    print(f"\n{'GRAPH LIFT VERDICT':^82}")
    print(thin)
    _print_verdict(report)
    print(f"\n{sep}\n")


def _print_metric_table(
    rows: list[DeltaMetrics],
    unit: str = "",
) -> None:
    headers = ["Metric", "Vector Only", "Hybrid", "Δ Absolute", "Δ Relative"]
    col_w = [24, 14, 14, 14, 14]
    header_line = "".join(h.ljust(w) for h, w in zip(headers, col_w))
    print(f"  {header_line}")
    print(f"  {'─' * sum(col_w)}")

    for d in rows:
        arrow = _arrow(d.absolute_delta, d.metric_name)
        suffix = f" {unit}" if unit else ""
        vals = [
            d.metric_name,
            f"{d.vector_only_value:.4f}{suffix}",
            f"{d.hybrid_value:.4f}{suffix}",
            f"{d.absolute_delta:+.4f}{suffix}",
            f"{d.relative_delta_pct:+.1f}% {arrow}",
        ]
        line = "".join(str(v).ljust(w) for v, w in zip(vals, col_w))
        print(f"  {line}")


def _print_latency_detail(vo: AggregateMetrics, hy: AggregateMetrics) -> None:
    col_w = [24, 14, 14]
    header = "".join(
        h.ljust(w) for h, w in zip(["Percentile", "Vector Only", "Hybrid"], col_w)
    )
    print(f"  {header}")
    print(f"  {'─' * sum(col_w)}")

    for label, vo_val, hy_val in [
        ("P50 (retrieval)", vo.retrieval_latency.p50_ms, hy.retrieval_latency.p50_ms),
        ("P95 (retrieval)", vo.retrieval_latency.p95_ms, hy.retrieval_latency.p95_ms),
        ("P99 (retrieval)", vo.retrieval_latency.p99_ms, hy.retrieval_latency.p99_ms),
        ("Mean (retrieval)", vo.retrieval_latency.mean_ms, hy.retrieval_latency.mean_ms),
        ("P50 (e2e)", vo.e2e_latency.p50_ms, hy.e2e_latency.p50_ms),
        ("P95 (e2e)", vo.e2e_latency.p95_ms, hy.e2e_latency.p95_ms),
        ("Mean (e2e)", vo.e2e_latency.mean_ms, hy.e2e_latency.mean_ms),
    ]:
        vals = [label, f"{vo_val:.1f} ms", f"{hy_val:.1f} ms"]
        line = "".join(str(v).ljust(w) for v, w in zip(vals, col_w))
        print(f"  {line}")


def _print_verdict(report: EvaluationReport) -> None:
    quality_deltas = [
        d for d in report.deltas
        if d.metric_name in {"context_recall", "faithfulness", "answer_relevance"}
    ]
    latency_delta = next(
        (d for d in report.deltas if d.metric_name == "retrieval_latency_p50"),
        None,
    )

    avg_quality_lift = 0.0
    if quality_deltas:
        avg_quality_lift = sum(d.relative_delta_pct for d in quality_deltas) / len(quality_deltas)

    latency_overhead = latency_delta.relative_delta_pct if latency_delta else 0.0

    recall_delta = next(
        (d for d in report.deltas if d.metric_name == "context_recall"), None
    )
    recall_lift = recall_delta.relative_delta_pct if recall_delta else 0.0

    print(f"  Context Recall lift (graph traversal):  {recall_lift:+.1f}%")
    print(f"  Average quality lift (3 RAGAS metrics): {avg_quality_lift:+.1f}%")
    print(f"  Retrieval latency overhead (P50):       {latency_overhead:+.1f}%")

    if avg_quality_lift > 5.0:
        print(f"\n  CONCLUSION: Neo4j graph traversal provides measurable quality gains.")
        print(f"  The {latency_overhead:+.1f}% latency cost is JUSTIFIED by {avg_quality_lift:+.1f}% quality lift.")
    elif avg_quality_lift > 0:
        print(f"\n  CONCLUSION: Graph traversal provides marginal improvement.")
        print(f"  Consider tuning traversal depth or graph density.")
    else:
        print(f"\n  CONCLUSION: Graph traversal does NOT improve quality in this dataset.")
        print(f"  Review knowledge graph density, entity extraction quality, and test coverage.")


def _arrow(delta: float, metric_name: str) -> str:
    is_latency = "latency" in metric_name
    if delta == 0:
        return "→"
    if is_latency:
        return "▼" if delta < 0 else "▲"
    return "▲" if delta > 0 else "▼"


# ──────────────────────────────────────────
# JSON Export (PRD §9.4)
# ──────────────────────────────────────────


def save_report_json(
    report: EvaluationReport,
    output_dir: str | Path = "eval_results",
) -> Path:
    """Serialize the report to a timestamped JSON file."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"eval_report_{timestamp}.json"
    filepath = out_dir / filename

    data = report.model_dump(mode="json")
    filepath.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    logger.info("Evaluation report saved to %s", filepath)
    return filepath
