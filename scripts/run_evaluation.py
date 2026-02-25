#!/usr/bin/env python3
"""CLI entry point for the evaluation framework (PRD §9).

Subcommands:
    evaluate  — Run ablation study (vector_only vs hybrid)
    generate  — Generate golden dataset from documents (cold-start)

Usage:
    # Run ablation study with RAGAS scoring
    python -m scripts.run_evaluation evaluate

    # Run without RAGAS (latency benchmarks only)
    python -m scripts.run_evaluation evaluate --no-ragas

    # Generate golden Q&A dataset (cold-start, PRD §9.3)
    python -m scripts.run_evaluation generate --documents docs/ --size 100
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.embedding.service import EmbeddingService
from app.evaluation.report import print_report, save_report_json
from app.evaluation.runner import EvaluationRunner
from app.evaluation.tracking import push_to_langsmith, push_to_mlflow
from app.persistence.graph_store import GraphStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Graph RAG Evaluation Framework (PRD §9)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="Sub-command")

    # ── evaluate ──
    eval_parser = sub.add_parser("evaluate", help="Run ablation study")
    eval_parser.add_argument(
        "--dataset", type=str, default=None,
        help="Path to evaluation dataset JSON (default: eval_datasets/golden_qa.json)",
    )
    eval_parser.add_argument("--top-k", type=int, default=10)
    eval_parser.add_argument("--depth", type=int, default=2)
    eval_parser.add_argument(
        "--no-ragas", action="store_true",
        help="Disable RAGAS scoring (latency benchmarks only)",
    )
    eval_parser.add_argument("--output-dir", type=str, default="eval_results")
    eval_parser.add_argument(
        "--push-langsmith", action="store_true",
        help="Push results to LangSmith (requires LANGCHAIN_API_KEY)",
    )
    eval_parser.add_argument(
        "--push-mlflow", action="store_true",
        help="Push results to MLflow (requires mlflow package)",
    )
    eval_parser.add_argument(
        "--log-level", type=str, default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )

    # ── generate ──
    gen_parser = sub.add_parser("generate", help="Generate golden dataset (cold-start)")
    gen_parser.add_argument(
        "--documents", type=str, required=True,
        help="Path to directory of .txt/.md files or a single file",
    )
    gen_parser.add_argument("--size", type=int, default=100, help="Number of Q&A pairs")
    gen_parser.add_argument(
        "--output", type=str, default="eval_datasets/golden_qa_generated.json",
    )
    gen_parser.add_argument(
        "--log-level", type=str, default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )

    args = parser.parse_args()
    if args.command is None:
        args.command = "evaluate"
    return args


async def cmd_evaluate(args: argparse.Namespace) -> None:
    """Run the ablation study."""
    settings = get_settings()

    log = logging.getLogger("evaluation")
    log.info("Loading embedding model...")
    embedding_service = EmbeddingService(settings.embedding)
    embedding_service.load_model()

    log.info("Connecting to Neo4j...")
    graph_store = GraphStore(settings.neo4j)
    async with graph_store:
        runner = EvaluationRunner(
            settings=settings,
            graph_store=graph_store,
            embedding_service=embedding_service,
            enable_ragas=not args.no_ragas,
            top_k=args.top_k,
            traversal_depth=args.depth,
        )

        report = await runner.run(dataset_path=args.dataset)

        print_report(report)

        report_path = save_report_json(report, output_dir=args.output_dir)
        log.info("JSON report saved to: %s", report_path)

        if args.push_langsmith:
            push_to_langsmith(report)
        if args.push_mlflow:
            push_to_mlflow(report)


async def cmd_generate(args: argparse.Namespace) -> None:
    """Generate golden dataset from documents."""
    from app.evaluation.testset_generator import generate_golden_dataset

    settings = get_settings()
    doc_path = Path(args.documents)

    documents: list[str] = []
    if doc_path.is_dir():
        for f in sorted(doc_path.glob("**/*")):
            if f.suffix in {".txt", ".md", ".rst"}:
                documents.append(f.read_text(encoding="utf-8"))
    elif doc_path.is_file():
        documents.append(doc_path.read_text(encoding="utf-8"))
    else:
        logging.error("Documents path not found: %s", doc_path)
        sys.exit(1)

    logging.info("Loaded %d documents from %s", len(documents), doc_path)

    out = await generate_golden_dataset(
        documents=documents,
        openai_settings=settings.openai,
        testset_size=args.size,
        output_path=args.output,
    )
    logging.info("Golden dataset generated: %s", out)
    logging.info("NEXT STEP: Have domain experts (SMEs) review and curate the dataset.")


async def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.command == "evaluate":
        await cmd_evaluate(args)
    elif args.command == "generate":
        await cmd_generate(args)


if __name__ == "__main__":
    asyncio.run(main())
