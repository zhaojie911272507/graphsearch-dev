"""Metrics tracking integration (PRD §9.4).

Supports pushing evaluation results to external observability platforms:
- LangSmith (primary, since langchain is already a dependency)
- MLflow (optional)
- Stdout fallback when no platform is configured

Environment variables:
  LANGCHAIN_TRACING_V2=true
  LANGCHAIN_API_KEY=ls-xxx
  LANGCHAIN_PROJECT=graph-rag-eval
"""

import json
import logging
import os
from typing import Any

from app.evaluation.schemas import EvaluationReport

logger = logging.getLogger(__name__)


def push_to_langsmith(report: EvaluationReport) -> bool:
    """Log evaluation metrics to LangSmith as a feedback/run.

    Requires LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY set.

    Returns:
        True if metrics were successfully pushed.
    """
    if not os.getenv("LANGCHAIN_API_KEY"):
        logger.info("LANGCHAIN_API_KEY not set — skipping LangSmith push")
        return False

    try:
        from langsmith import Client

        client = Client()
        project = os.getenv("LANGCHAIN_PROJECT", "graph-rag-eval")

        metrics: dict[str, Any] = {
            "dataset": report.dataset_name,
            "num_queries": report.vector_only.num_queries,
        }

        for prefix, agg in [("vo", report.vector_only), ("hy", report.hybrid)]:
            metrics.update({
                f"{prefix}/context_precision": agg.avg_context_precision,
                f"{prefix}/context_recall": agg.avg_context_recall,
                f"{prefix}/faithfulness": agg.avg_faithfulness,
                f"{prefix}/answer_relevance": agg.avg_answer_relevance,
                f"{prefix}/retrieval_latency_p50": agg.retrieval_latency.p50_ms,
                f"{prefix}/retrieval_latency_p95": agg.retrieval_latency.p95_ms,
                f"{prefix}/e2e_latency_p50": agg.e2e_latency.p50_ms,
            })

        for delta in report.deltas:
            metrics[f"delta/{delta.metric_name}"] = delta.relative_delta_pct

        dataset_name = f"eval-{report.dataset_name}"
        try:
            client.read_dataset(dataset_name=dataset_name)
        except Exception:
            client.create_dataset(
                dataset_name=dataset_name,
                description="Graph RAG evaluation metrics",
            )

        client.create_example(
            inputs={"run_type": "ablation_study", "dataset": report.dataset_name},
            outputs=metrics,
            dataset_name=dataset_name,
        )

        logger.info(
            "Evaluation metrics pushed to LangSmith project '%s'", project
        )
        return True

    except ImportError:
        logger.warning("langsmith package not installed — skipping LangSmith push")
        return False
    except Exception as exc:
        logger.warning("Failed to push to LangSmith: %s", exc)
        return False


def push_to_mlflow(report: EvaluationReport, experiment_name: str = "graph-rag-eval") -> bool:
    """Log evaluation metrics to MLflow (optional).

    Requires mlflow package and MLFLOW_TRACKING_URI.

    Returns:
        True if metrics were successfully logged.
    """
    try:
        import mlflow

        mlflow.set_experiment(experiment_name)

        with mlflow.start_run(run_name=f"eval-{report.dataset_name}"):
            for prefix, agg in [("vector_only", report.vector_only), ("hybrid", report.hybrid)]:
                mlflow.log_metrics({
                    f"{prefix}.context_precision": agg.avg_context_precision,
                    f"{prefix}.context_recall": agg.avg_context_recall,
                    f"{prefix}.faithfulness": agg.avg_faithfulness,
                    f"{prefix}.answer_relevance": agg.avg_answer_relevance,
                    f"{prefix}.retrieval_latency_p50": agg.retrieval_latency.p50_ms,
                    f"{prefix}.e2e_latency_p50": agg.e2e_latency.p50_ms,
                })

            for delta in report.deltas:
                mlflow.log_metric(f"delta.{delta.metric_name}", delta.relative_delta_pct)

            mlflow.log_dict(
                report.model_dump(mode="json"),
                "eval_report.json",
            )

        logger.info("Evaluation metrics logged to MLflow experiment '%s'", experiment_name)
        return True

    except ImportError:
        logger.warning("mlflow package not installed — skipping MLflow push")
        return False
    except Exception as exc:
        logger.warning("Failed to log to MLflow: %s", exc)
        return False
