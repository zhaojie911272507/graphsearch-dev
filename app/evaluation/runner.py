"""Evaluation runner — orchestrates the ablation study (PRD §9.2).

For every evaluation case, runs both retrieval modes (vector_only, hybrid),
collects latency breakdowns, invokes RAGAS for quality scoring, and
assembles the final comparison report.
"""

import logging
import time

from langchain_openai import ChatOpenAI

from app.config import Settings
from app.embedding.service import EmbeddingService
from app.evaluation.dataset import load_dataset
from app.evaluation.metrics import (
    aggregate_results,
    build_ragas_llm,
    compute_deltas,
    compute_ragas_scores,
)
from app.evaluation.schemas import (
    EvalCase,
    EvalDataset,
    EvaluationReport,
    LatencyBreakdown,
    RagasScores,
    RetrievalMode,
    SingleQueryResult,
)
from app.persistence.graph_store import GraphStore
from app.retrieval.retriever import GraphRetriever

logger = logging.getLogger(__name__)

_GENERATION_SYSTEM_PROMPT = """You are a knowledgeable assistant that answers questions
based on the provided context from a knowledge graph. Use the context to give accurate,
well-structured answers. If the context doesn't contain enough information, say so honestly."""


class EvaluationRunner:
    """Runs the full ablation study: vector_only vs hybrid (PRD §9.2).

    Args:
        settings: Application settings (LLM config, etc.).
        graph_store: Connected Neo4j adapter.
        embedding_service: Loaded embedding service.
        enable_ragas: Whether to run RAGAS scoring (set False for latency-only benchmarks).
        top_k: Number of chunks for vector search.
        traversal_depth: Graph traversal hops for hybrid mode.
    """

    def __init__(
        self,
        settings: Settings,
        graph_store: GraphStore,
        embedding_service: EmbeddingService,
        *,
        enable_ragas: bool = True,
        top_k: int = 10,
        traversal_depth: int = 2,
    ) -> None:
        self._settings = settings
        self._retriever = GraphRetriever(graph_store, embedding_service)
        self._top_k = top_k
        self._traversal_depth = traversal_depth
        self._enable_ragas = enable_ragas

        self._llm = ChatOpenAI(
            api_key=settings.openai.api_key,  # type: ignore[arg-type]
            base_url=settings.openai.base_url,
            model=settings.openai.model,
            temperature=0.1,
        )
        self._evaluator_llm = build_ragas_llm(settings.openai) if enable_ragas else None

    async def run(
        self,
        dataset: EvalDataset | None = None,
        dataset_path: str | None = None,
    ) -> EvaluationReport:
        """Execute the complete ablation study.

        Args:
            dataset: Pre-loaded dataset (takes precedence).
            dataset_path: Path to dataset JSON (used if dataset is None).

        Returns:
            EvaluationReport with per-query and aggregate results.
        """
        if dataset is None:
            dataset = load_dataset(dataset_path)

        logger.info(
            "Starting ablation study: %d cases, modes=[vector_only, hybrid], "
            "top_k=%d, depth=%d, ragas=%s",
            len(dataset.cases),
            self._top_k,
            self._traversal_depth,
            self._enable_ragas,
        )

        all_results: list[SingleQueryResult] = []

        for i, case in enumerate(dataset.cases, start=1):
            logger.info(
                "[%d/%d] %s", i, len(dataset.cases), case.question[:80]
            )

            vo_result = await self._evaluate_single(case, RetrievalMode.VECTOR_ONLY)
            hy_result = await self._evaluate_single(case, RetrievalMode.HYBRID)

            all_results.extend([vo_result, hy_result])

        vo_agg = aggregate_results(all_results, RetrievalMode.VECTOR_ONLY)
        hy_agg = aggregate_results(all_results, RetrievalMode.HYBRID)
        deltas = compute_deltas(vo_agg, hy_agg)

        report = EvaluationReport(
            dataset_name=dataset.name,
            vector_only=vo_agg,
            hybrid=hy_agg,
            deltas=deltas,
            per_query_results=all_results,
        )

        logger.info(
            "Ablation study complete: %d queries × 2 modes = %d results",
            len(dataset.cases),
            len(all_results),
        )
        return report

    async def _evaluate_single(
        self,
        case: EvalCase,
        mode: RetrievalMode,
    ) -> SingleQueryResult:
        """Run one query in one mode, measure latency and quality."""
        vector_only = mode == RetrievalMode.VECTOR_ONLY

        e2e_start = time.monotonic()

        # ── Retrieval ──
        t_ret_start = time.monotonic()
        context = await self._retriever.retrieve(
            query=case.question,
            top_k=self._top_k,
            traversal_depth=self._traversal_depth,
            vector_only=vector_only,
        )
        total_retrieval_ms = (time.monotonic() - t_ret_start) * 1000

        retrieved_contexts = [c.content for c in context.chunks]
        retrieved_entity_names = [e.name for e in context.entities]

        # ── LLM Generation ──
        generated_answer = ""
        llm_gen_ms = 0.0
        if context.chunks:
            t_gen_start = time.monotonic()
            generated_answer = await self._generate_answer(
                case.question, context.formatted_context
            )
            llm_gen_ms = (time.monotonic() - t_gen_start) * 1000

        total_e2e_ms = (time.monotonic() - e2e_start) * 1000

        latency = LatencyBreakdown(
            total_retrieval_ms=round(total_retrieval_ms, 2),
            llm_generation_ms=round(llm_gen_ms, 2),
            total_e2e_ms=round(total_e2e_ms, 2),
        )

        # ── RAGAS Scoring (PRD §9.2) ──
        ragas_scores = RagasScores()
        if self._enable_ragas and self._evaluator_llm and generated_answer:
            ragas_scores = await compute_ragas_scores(
                question=case.question,
                generated_answer=generated_answer,
                retrieved_contexts=retrieved_contexts,
                expected_answer=case.expected_answer,
                evaluator_llm=self._evaluator_llm,
            )

        return SingleQueryResult(
            question=case.question,
            mode=mode,
            generated_answer=generated_answer,
            expected_answer=case.expected_answer,
            retrieved_contexts=retrieved_contexts,
            expected_contexts=case.expected_contexts,
            retrieved_entity_names=retrieved_entity_names,
            num_chunks=len(context.chunks),
            num_entities=len(context.entities),
            num_relations=len(context.relations),
            latency=latency,
            ragas_scores=ragas_scores,
        )

    async def _generate_answer(self, question: str, context: str) -> str:
        """Generate an answer using the LLM given retrieved context."""
        user_prompt = (
            f"Context from knowledge graph:\n{context}\n\n"
            f"Question: {question}\n\n"
            f"Answer based on the above context:"
        )
        try:
            response = await self._llm.ainvoke(
                [
                    {"role": "system", "content": _GENERATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ]
            )
            content = response.content
            return content if isinstance(content, str) else str(content)
        except Exception as exc:
            logger.warning("LLM generation failed: %s", exc)
            return ""
