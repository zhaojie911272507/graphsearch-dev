"""Evaluation and monitoring API routes.

Provides endpoints for:
- RAGAS metrics tracking
- Pipeline configuration
- Prompt template management
- Ablation studies
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import GraphStoreDep
from app.api.schemas.evaluation import (
    AblationStudyResponseSchema,
    EvaluationMetricSchema,
    EvaluationMetricsResponseSchema,
    EvaluationTrendResponseSchema,
    MetricTimeSeriesSchema,
    PipelineConfigCreateSchema,
    PipelineConfigListResponseSchema,
    PipelineConfigSchema,
    PromptTemplateCreateSchema,
    PromptTemplateSchema,
    PromptTestRequestSchema,
    PromptTestResponseSchema,
    QueryEvaluationSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluation", tags=["Evaluation & Monitoring"])


@router.get(
    "/metrics",
    response_model=EvaluationMetricsResponseSchema,
    summary="Get evaluation metrics",
    description="Get current RAGAS evaluation metrics.",
)
async def get_evaluation_metrics(
    store: GraphStoreDep,
    days: int = Query(default=7, ge=1, le=30),
) -> EvaluationMetricsResponseSchema:
    """Get current evaluation metrics."""
    try:
        metrics = await store.get_evaluation_metrics(days=days)

        processed_metrics = {}
        for name, data in metrics.get("metrics", {}).items():
            value = data.get("value", 0.0)
            previous = data.get("previous_value")
            change = data.get("change")

            if change is None and previous is not None:
                change = value - previous if previous else 0

            trend = "stable"
            if change:
                trend = "up" if change > 0 else "down" if change < 0 else "stable"

            processed_metrics[name] = EvaluationMetricSchema(
                name=name,
                value=value,
                previous_value=previous,
                change=change,
                trend=trend,
                target=data.get("target"),
            )

        overall = sum(m.value for m in processed_metrics.values()) / len(processed_metrics) if processed_metrics else 0.0

        return EvaluationMetricsResponseSchema(
            metrics=processed_metrics,
            overall_score=round(overall, 3),
            evaluated_queries=metrics.get("evaluated_queries", 0),
            evaluation_period=metrics.get("period", {}),
        )
    except Exception as exc:
        logger.exception("Failed to get evaluation metrics: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get evaluation metrics: {exc}",
        ) from exc


@router.get(
    "/trend",
    response_model=EvaluationTrendResponseSchema,
    summary="Get metrics trend",
    description="Get evaluation metrics trend over time.",
)
async def get_metrics_trend(
    store: GraphStoreDep,
    start_date: datetime = Query(..., description="Start date"),
    end_date: datetime = Query(..., description="End date"),
    granularity: str = Query(default="day", description="day, week, month"),
    metrics: list[str] = Query(default=["precision", "recall", "faithfulness", "relevance"]),
) -> EvaluationTrendResponseSchema:
    """Get metrics trend over time."""
    try:
        trend_data = await store.get_metrics_trend(
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
            metric_names=metrics,
        )

        time_series = []
        for metric_name in metrics:
            data_points = trend_data.get(metric_name, [])
            values = [dp.get("value", 0) for dp in data_points]
            time_series.append(MetricTimeSeriesSchema(
                metric_name=metric_name,
                data_points=data_points,
                avg_value=sum(values) / len(values) if values else 0.0,
                min_value=min(values) if values else 0.0,
                max_value=max(values) if values else 0.0,
            ))

        return EvaluationTrendResponseSchema(
            start_date=start_date,
            end_date=end_date,
            granularity=granularity,
            metrics=time_series,
        )
    except Exception as exc:
        logger.exception("Failed to get metrics trend: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics trend: {exc}",
        ) from exc


@router.get(
    "/ablation-study",
    response_model=AblationStudyResponseSchema,
    summary="Get ablation study results",
    description="Compare vector-only vs hybrid retrieval performance.",
)
async def get_ablation_study(
    store: GraphStoreDep,
    days: int = Query(default=7, ge=1, le=30),
) -> AblationStudyResponseSchema:
    """Get ablation study comparing retrieval strategies."""
    try:
        study = await store.get_ablation_study(days=days)

        def process_metrics(raw_metrics: dict) -> dict[str, EvaluationMetricSchema]:
            result = {}
            for name, data in raw_metrics.items():
                value = data.get("value", 0.0)
                result[name] = EvaluationMetricSchema(
                    name=name,
                    value=value,
                    target=data.get("target"),
                )
            return result

        vector_metrics = process_metrics(study.get("vector_only", {}))
        hybrid_metrics = process_metrics(study.get("hybrid", {}))

        improvement = {}
        for key in hybrid_metrics:
            if key in vector_metrics and vector_metrics[key].value > 0:
                imp = ((hybrid_metrics[key].value - vector_metrics[key].value) /
                       vector_metrics[key].value * 100)
                improvement[key] = round(imp, 2)

        return AblationStudyResponseSchema(
            vector_only=vector_metrics,
            hybrid=hybrid_metrics,
            improvement=improvement,
            statistical_significance=study.get("p_values", {}),
            sample_size=study.get("sample_size", 0),
        )
    except Exception as exc:
        logger.exception("Failed to get ablation study: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ablation study: {exc}",
        ) from exc


@router.get(
    "/queries",
    response_model=list[QueryEvaluationSchema],
    summary="List query evaluations",
)
async def list_query_evaluations(
    store: GraphStoreDep,
    days: int = Query(default=7, ge=1, le=30),
    min_precision: float | None = Query(default=None, description="Filter by min precision"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[QueryEvaluationSchema]:
    """List individual query evaluations."""
    try:
        evaluations = await store.get_query_evaluations(
            days=days,
            min_precision=min_precision,
            limit=limit,
        )

        return [
            QueryEvaluationSchema(
                id=UUID(e["id"]),
                query_text=e["query_text"],
                context_precision=e.get("context_precision", 0.0),
                context_recall=e.get("context_recall", 0.0),
                faithfulness=e.get("faithfulness", 0.0),
                answer_relevance=e.get("answer_relevance", 0.0),
                latency_ms=e.get("latency_ms", 0.0),
                retrieved_chunks=e.get("retrieved_chunks", 0),
                retrieved_entities=e.get("retrieved_entities", 0),
                created_at=datetime.fromisoformat(e["created_at"].replace("Z", "+00:00")) if isinstance(e["created_at"], str) else e["created_at"],
            )
            for e in evaluations
        ]
    except Exception as exc:
        logger.exception("Failed to list query evaluations: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list query evaluations: {exc}",
        ) from exc


@router.get(
    "/pipeline/configs",
    response_model=PipelineConfigListResponseSchema,
    summary="List pipeline configurations",
)
async def list_pipeline_configs(
    store: GraphStoreDep,
    include_inactive: bool = Query(default=False),
) -> PipelineConfigListResponseSchema:
    """List all pipeline configurations."""
    try:
        configs = await store.get_pipeline_configs()

        active_version = None
        config_list = []
        for c in configs:
            config = PipelineConfigSchema(
                version=c["version"],
                retrieval=c.get("retrieval", {}),
                generation=c.get("generation", {}),
                created_at=datetime.fromisoformat(c["created_at"].replace("Z", "+00:00")) if isinstance(c["created_at"], str) else c["created_at"],
                created_by=c["created_by"],
                is_active=c.get("is_active", False),
            )
            if config.is_active:
                active_version = config.version
            config_list.append(config)

        return PipelineConfigListResponseSchema(
            configs=config_list,
            active_version=active_version,
        )
    except Exception as exc:
        logger.exception("Failed to list pipeline configs: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list pipeline configs: {exc}",
        ) from exc


@router.post(
    "/pipeline/configs",
    response_model=PipelineConfigSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create pipeline configuration",
)
async def create_pipeline_config(
    config: PipelineConfigCreateSchema,
    store: GraphStoreDep,
) -> PipelineConfigSchema:
    """Create a new pipeline configuration."""
    try:
        existing = await store.get_pipeline_config(config.version)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Pipeline config version {config.version} already exists",
            )

        created = await store.create_pipeline_config(
            version=config.version,
            retrieval=config.retrieval,
            generation=config.generation,
            created_by="current_user",
            change_summary=config.change_summary,
        )

        return PipelineConfigSchema(
            version=created["version"],
            retrieval=created.get("retrieval", {}),
            generation=created.get("generation", {}),
            created_at=datetime.fromisoformat(created["created_at"].replace("Z", "+00:00")) if isinstance(created["created_at"], str) else datetime.utcnow(),
            created_by=created["created_by"],
            is_active=created.get("is_active", False),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create pipeline config: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create pipeline config: {exc}",
        ) from exc


@router.post(
    "/pipeline/configs/{version}/activate",
    summary="Activate pipeline configuration",
)
async def activate_pipeline_config(
    version: str,
    store: GraphStoreDep,
) -> dict:
    """Activate a pipeline configuration."""
    try:
        existing = await store.get_pipeline_config(version)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pipeline config version {version} not found",
            )

        await store.activate_pipeline_config(version)

        return {
            "success": True,
            "message": f"Activated pipeline config {version}",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to activate pipeline config: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate pipeline config: {exc}",
        ) from exc


@router.get(
    "/prompts",
    response_model=list[PromptTemplateSchema],
    summary="List prompt templates",
)
async def list_prompt_templates(
    store: GraphStoreDep,
    template_type: str | None = Query(default=None),
) -> list[PromptTemplateSchema]:
    """List all prompt templates."""
    try:
        templates = await store.get_prompt_templates(
            template_type=template_type,
        )

        return [
            PromptTemplateSchema(
                id=UUID(t["id"]),
                name=t["name"],
                template_type=t["template_type"],
                content=t["content"],
                variables=t.get("variables", []),
                version=t["version"],
                is_active=t.get("is_active", False),
                created_at=datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")) if isinstance(t["created_at"], str) else t["created_at"],
                updated_at=datetime.fromisoformat(t["updated_at"].replace("Z", "+00:00")) if isinstance(t["updated_at"], str) else t["updated_at"],
                created_by=t["created_by"],
            )
            for t in templates
        ]
    except Exception as exc:
        logger.exception("Failed to list prompt templates: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list prompt templates: {exc}",
        ) from exc


@router.post(
    "/prompts",
    response_model=PromptTemplateSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create prompt template",
)
async def create_prompt_template(
    template: PromptTemplateCreateSchema,
    store: GraphStoreDep,
) -> PromptTemplateSchema:
    """Create a new prompt template."""
    try:
        created = await store.create_prompt_template(
            name=template.name,
            template_type=template.template_type,
            content=template.content,
            variables=template.variables,
            version=template.version,
            created_by="current_user",
        )

        return PromptTemplateSchema(
            id=UUID(created["id"]),
            name=created["name"],
            template_type=created["template_type"],
            content=created["content"],
            variables=created.get("variables", []),
            version=created["version"],
            is_active=created.get("is_active", False),
            created_at=datetime.fromisoformat(created["created_at"].replace("Z", "+00:00")) if isinstance(created["created_at"], str) else datetime.utcnow(),
            updated_at=datetime.fromisoformat(created["updated_at"].replace("Z", "+00:00")) if isinstance(created["updated_at"], str) else datetime.utcnow(),
            created_by=created["created_by"],
        )
    except Exception as exc:
        logger.exception("Failed to create prompt template: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create prompt template: {exc}",
        ) from exc


@router.post(
    "/prompts/test",
    response_model=PromptTestResponseSchema,
    summary="Test prompt template",
)
async def test_prompt_template(
    request: PromptTestRequestSchema,
    store: GraphStoreDep,
) -> PromptTestResponseSchema:
    """Test a prompt template with sample input."""
    try:
        template_content = request.template_content
        if not template_content and request.template_id:
            template = await store.get_prompt_template(str(request.template_id))
            if template:
                template_content = template["content"]

        if not template_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either template_id or template_content is required",
            )

        rendered = template_content
        for var_name, var_value in request.variables.items():
            rendered = rendered.replace(f"{{{{{var_name}}}}}", var_value)

        return PromptTestResponseSchema(
            rendered_prompt=rendered,
            latency_ms=0.0,
            tokens_used=len(rendered) // 4,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to test prompt: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test prompt: {exc}",
        ) from exc
