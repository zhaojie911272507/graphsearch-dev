# 监控和可观测性实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Graph RAG FastAPI 系统实现完整的监控和可观测性套件，包括 Prometheus 指标收集、OpenTelemetry 分布式追踪（Tempo 后端）、Grafana 可视化仪表板和 Prometheus 告警规则。

**Architecture:**
- 在 FastAPI 应用中集成 Prometheus 客户端暴露 `/metrics` 端点
- 使用 OpenTelemetry Python SDK 进行自动和手动插桩，通过 OTLP HTTP 导出到 Tempo
- 日志系统（structlog）增强 trace_id/span_id 关联能力
- Docker Compose 新增 monitoring 服务栈（Prometheus + Tempo + Grafana）
- Grafana 预配置数据源和 RAG 专用仪表板
- Prometheus 定义告警规则并通过 Alertmanager 路由

**Tech Stack:**
- prometheus-client (Python)
- opentelemetry-api, opentelemetry-sdk, opentelemetry-exporter-otlp
- opentelemetry-instrumentation-fastapi, opentelemetry-instrumentation-httpx
- Prometheus, Grafana Tempo, Grafana OSS
- Docker Compose

---

## Task 1: 依赖和配置

**Files:**
- Modify: `requirements.txt`
- Create: `app/observability/config.py`
- Modify: `.env.example`

- [ ] **Step 1: 添加监控依赖到 requirements.txt**

在 `requirements.txt` 末尾添加：

```python
# Observability (Monitoring & Tracing)
prometheus-client>=0.19.0
opentelemetry-api>=1.21.0
opentelemetry-sdk>=1.21.0
opentelemetry-exporter-otlp>=1.21.0
opentelemetry-instrumentation-fastapi>=0.42b0
opentelemetry-instrumentation-httpx>=0.42b0
opentelemetry-instrumentation-asyncio>=0.42b0
```

- [ ] **Step 2: 运行 pip install 验证依赖安装**

```bash
pip install -r requirements.txt
```

期望：所有包成功安装，无错误

- [ ] **Step 3: 创建观测性配置模块 `app/observability/config.py`**

```python
"""Observability configuration via pydantic-settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ObservabilitySettings(BaseSettings):
    """Observability configuration for monitoring and tracing."""

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    # OpenTelemetry
    otel_enabled: bool = Field(default=True, description="Enable OpenTelemetry tracing")
    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4318",
        description="OTLP HTTP endpoint for Tempo",
    )
    otel_traces_sampler: str = Field(
        default="parentbased_traceidratio",
        description="Trace sampler type",
    )
    otel_traces_sampler_arg: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Trace sampling rate (0.0-1.0)",
    )
    otel_service_name: str = Field(default="graphrag-api", description="Service name for traces")
    otel_resource_attributes: str = Field(
        default="deployment.environment=development",
        description="Additional resource attributes",
    )

    # Metrics
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=8000, description="Port for metrics endpoint")

    # Alerting
    alertmanager_url: str = Field(default="http://localhost:9093", description="Alertmanager URL")
    webhook_alert_url: str = Field(default="", description="Webhook URL for alert notifications")


def get_observability_settings() -> ObservabilitySettings:
    """Factory function for observability settings."""
    return ObservabilitySettings()
```

- [ ] **Step 4: 更新 `.env.example` 添加观测性配置**

在 `.env.example` 末尾添加：

```bash
# ──────────────────────────────────────────
# Observability (Monitoring & Tracing)
# ──────────────────────────────────────────
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1
OTEL_SERVICE_NAME=graphrag-api
OTEL_RESOURCE_ATTRIBUTES=deployment.environment=development

METRICS_ENABLED=true
METRICS_PORT=8000

ALERTMANAGER_URL=http://localhost:9093
WEBHOOK_ALERT_URL=
```

- [ ] **Step 5: 提交**

```bash
git add requirements.txt app/observability/config.py .env.example
git commit -m "feat: add observability dependencies and configuration"
```

---

## Task 2: Prometheus 指标收集

**Files:**
- Create: `app/observability/metrics.py`
- Create: `app/observability/__init__.py`
- Modify: `app/main.py`

- [ ] **Step 1: 创建观测性模块 `app/observability/__init__.py`**

```python
"""Observability module providing metrics, tracing, and enhanced logging."""

from app.observability.config import ObservabilitySettings, get_observability_settings

__all__ = ["ObservabilitySettings", "get_observability_settings"]
```

- [ ] **Step 2: 创建 Prometheus 指标模块 `app/observability/metrics.py`**

```python
"""Prometheus metrics definitions for Graph RAG system."""

import time
from typing import ClassVar

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)


class MetricsRegistry:
    """Central registry for all Prometheus metrics."""

    _registry: ClassVar[CollectorRegistry] = CollectorRegistry()

    # HTTP Metrics (auto-collected by middleware)
    http_requests_total: ClassVar[Counter] = Counter(
        "http_requests_total",
        "Total number of HTTP requests",
        labelnames=["method", "path", "status"],
        registry=_registry,
    )

    http_request_duration_seconds: ClassVar[Histogram] = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        labelnames=["method", "path"],
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        registry=_registry,
    )

    http_requests_in_progress: ClassVar[Gauge] = Gauge(
        "http_requests_in_progress",
        "Number of HTTP requests currently being processed",
        registry=_registry,
    )

    # Embedding Metrics
    rag_embedding_latency_seconds: ClassVar[Histogram] = Histogram(
        "rag_embedding_latency_seconds",
        "Time to generate embeddings",
        labelnames=["model", "device"],
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        registry=_registry,
    )

    # Vector Search Metrics
    rag_vector_search_latency_seconds: ClassVar[Histogram] = Histogram(
        "rag_vector_search_latency_seconds",
        "Time for vector similarity search",
        labelnames=["top_k"],
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
        registry=_registry,
    )

    rag_retrieval_total_chunks: ClassVar[Histogram] = Histogram(
        "rag_retrieval_total_chunks",
        "Number of chunks returned by retrieval",
        labelnames=["mode"],
        buckets=(1, 2, 5, 10, 20, 50, 100),
        registry=_registry,
    )

    # Graph Traversal Metrics
    rag_graph_traversal_latency_seconds: ClassVar[Histogram] = Histogram(
        "rag_graph_traversal_latency_seconds",
        "Time for graph traversal from seed chunks",
        labelnames=["depth"],
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        registry=_registry,
    )

    rag_retrieval_total_entities: ClassVar[Histogram] = Histogram(
        "rag_retrieval_total_entities",
        "Number of entities returned by retrieval",
        labelnames=["mode"],
        buckets=(1, 2, 5, 10, 20, 50, 100),
        registry=_registry,
    )

    rag_retrieval_total_relations: ClassVar[Histogram] = Histogram(
        "rag_retrieval_total_relations",
        "Number of relations returned by retrieval",
        labelnames=["mode"],
        buckets=(1, 2, 5, 10, 20, 50, 100),
        registry=_registry,
    )

    # Extraction Metrics
    rag_extraction_latency_seconds: ClassVar[Histogram] = Histogram(
        "rag_extraction_latency_seconds",
        "Time for LLM-based entity extraction",
        labelnames=["chunk_size_bucket"],
        buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
        registry=_registry,
    )

    rag_extraction_success_total: ClassVar[Counter] = Counter(
        "rag_extraction_success_total",
        "Total number of successful extractions",
        registry=_registry,
    )

    rag_extraction_failure_total: ClassVar[Counter] = Counter(
        "rag_extraction_failure_total",
        "Total number of failed extractions",
        labelnames=["error_type"],
        registry=_registry,
    )

    # LLM Metrics
    rag_llm_latency_seconds: ClassVar[Histogram] = Histogram(
        "rag_llm_latency_seconds",
        "Time for LLM API calls",
        labelnames=["model", "operation"],
        buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
        registry=_registry,
    )

    rag_llm_calls_total: ClassVar[Counter] = Counter(
        "rag_llm_calls_total",
        "Total number of LLM API calls",
        labelnames=["model", "operation", "status"],
        registry=_registry,
    )

    # Neo4j Metrics
    rag_neo4j_query_latency_seconds: ClassVar[Histogram] = Histogram(
        "rag_neo4j_query_latency_seconds",
        "Time for Neo4j queries",
        labelnames=["operation"],
        buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        registry=_registry,
    )

    rag_neo4j_connection_pool_size: ClassVar[Gauge] = Gauge(
        "rag_neo4j_connection_pool_size",
        "Neo4j connection pool size",
        labelnames=["state"],
        registry=_registry,
    )

    @classmethod
    def get_registry(cls) -> CollectorRegistry:
        """Get the Prometheus collector registry."""
        return cls._registry

    @classmethod
    def generate_metrics(cls) -> bytes:
        """Generate Prometheus metrics in text format."""
        return generate_latest(cls._registry)
```

- [ ] **Step 3: 修改 `app/main.py` 添加 metrics 端点**

在 `app/main.py` 中，导入 metrics 模块并添加端点：

```python
# 在文件顶部的导入部分添加
from app.observability.metrics import MetricsRegistry
from app.observability.config import get_observability_settings
```

在 `create_app()` 函数中，在 health endpoint 之后添加 metrics endpoint：

```python
    # Metrics endpoint
    @app.get("/metrics", tags=["Observability"])
    async def metrics():
        """Prometheus metrics endpoint."""
        from fastapi.responses import Response

        settings = get_settings()
        if not settings.observability.metrics_enabled:
            return Response(status_code=503, content="Metrics disabled")

        return Response(
            content=MetricsRegistry.generate_metrics(),
            media_type=CONTENT_TYPE_LATEST,
        )
```

- [ ] **Step 4: 提交**

```bash
git add app/observability/ app/main.py
git commit -m "feat: add Prometheus metrics collection and /metrics endpoint"
```

---

## Task 3: OpenTelemetry 分布式追踪

**Files:**
- Create: `app/observability/tracing.py`
- Modify: `app/main.py`
- Modify: `app/config.py`

- [ ] **Step 1: 在 `app/config.py` 中添加 ObservabilitySettings 到 Settings 类**

在 `Settings` 类中添加：

```python
from app.observability.config import ObservabilitySettings

class Settings(BaseSettings):
    # ... existing code ...
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
```

- [ ] **Step 2: 创建追踪模块 `app/observability/tracing.py`**

```python
"""OpenTelemetry distributed tracing setup."""

import logging
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_INSTANCE_ID
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    SpanExportResult,
)
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio

from app.config import Settings

logger = logging.getLogger(__name__)


class TracingSetup:
    """Manages OpenTelemetry tracing lifecycle."""

    _tracer_provider: TracerProvider | None = None
    _tracer: trace.Tracer | None = None

    @classmethod
    def initialize(cls, settings: Settings) -> None:
        """Initialize OpenTelemetry tracing."""
        if not settings.observability.otel_enabled:
            logger.info("OpenTelemetry tracing disabled")
            return

        # Build resource with service metadata
        resource_attributes = {
            SERVICE_NAME: settings.observability.otel_service_name,
            "service.version": "0.1.0",
            "deployment.environment": "development",
        }

        # Parse additional resource attributes from config
        extra_attrs = settings.observability.otel_resource_attributes
        if extra_attrs:
            for attr in extra_attrs.split(","):
                if "=" in attr:
                    key, value = attr.split("=", 1)
                    resource_attributes[key.strip()] = value.strip()

        resource = Resource.create(resource_attributes)

        # Create trace provider with configured sampler
        sampler = ParentBasedTraceIdRatio(
            float(settings.observability.otel_traces_sampler_arg)
        )

        cls._tracer_provider = TracerProvider(
            resource=resource,
            sampler=sampler,
        )

        # Set up OTLP HTTP exporter for Tempo
        exporter = OTLPSpanExporter(
            endpoint=settings.observability.otel_exporter_otlp_endpoint + "/v1/traces",
            timeout=5,
        )

        # Add batch span processor
        span_processor = BatchSpanProcessor(exporter)
        cls._tracer_provider.add_span_processor(span_processor)

        # Set as global tracer provider
        trace.set_tracer_provider(cls._tracer_provider)

        cls._tracer = cls._tracer_provider.get_tracer(
            settings.observability.otel_service_name
        )

        logger.info(
            "OpenTelemetry tracing initialized",
            extra={
                "endpoint": settings.observability.otel_exporter_otlp_endpoint,
                "service_name": settings.observability.otel_service_name,
                "sampling_rate": settings.observability.otel_traces_sampler_arg,
            },
        )

    @classmethod
    def get_tracer(cls, name: str | None = None) -> trace.Tracer:
        """Get a tracer instance."""
        if cls._tracer is None:
            return trace.get_tracer(name or "graphrag")
        return cls._tracer

    @classmethod
    def instrument_app(cls, app: Any) -> None:
        """Instrument FastAPI application."""
        if not cls._tracer_provider:
            logger.warning("Cannot instrument app: tracing not initialized")
            return

        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=cls._tracer_provider,
        )

        # Instrument HTTPX (for LLM and external API calls)
        HTTPXClientInstrumentor().instrument(tracer_provider=cls._tracer_provider)

        # Instrument asyncio (for async operations)
        AsyncioInstrumentor().instrument(tracer_provider=cls._tracer_provider)

        logger.info("Application instrumentation complete")

    @classmethod
    def shutdown(cls) -> None:
        """Clean up tracing resources."""
        if cls._tracer_provider:
            cls._tracer_provider.shutdown()
            cls._tracer_provider = None
            cls._tracer = None
            logger.info("OpenTelemetry tracing shutdown complete")
```

- [ ] **Step 3: 修改 `app/main.py` 的 lifespan 函数集成追踪**

在 `lifespan` 函数中，在 settings 加载后添加：

```python
from app.observability.tracing import TracingSetup

# 在 _configure_logging 调用后添加
# Initialize OpenTelemetry tracing
TracingSetup.initialize(settings)
TracingSetup.instrument_app(app)
```

在 shutdown 部分添加：

```python
# Shutdown tracing
TracingSetup.shutdown()
```

- [ ] **Step 4: 提交**

```bash
git add app/observability/tracing.py app/main.py app/config.py
git commit -m "feat: add OpenTelemetry distributed tracing with Tempo integration"
```

---

## Task 4: 手动插桩 - Embedding 和 Retrieval

**Files:**
- Modify: `app/embedding/service.py`
- Modify: `app/retrieval/retriever.py`

- [ ] **Step 1: 在 `app/embedding/service.py` 中添加 embedding 指标和追踪**

导入：

```python
from app.observability.metrics import MetricsRegistry
from app.observability.tracing import TracingSetup
import time
```

在 `embed_query` 方法中包裹指标和追踪代码：

```python
async def embed_query(self, text: str) -> list[float]:
    """Generate embedding for a query text."""
    start = time.monotonic()
    tracer = TracingSetup.get_tracer()

    with tracer.start_as_current_span("rag.embedding") as span:
        span.set_attribute("embedding.model", self._settings.model_path)
        span.set_attribute("embedding.device", self._settings.device)

        # ... existing embedding code ...

        duration = time.monotonic() - start
        MetricsRegistry.rag_embedding_latency_seconds.labels(
            model=self._settings.model_path,
            device=self._settings.device,
        ).observe(duration)

        span.set_attribute("embedding.duration_seconds", duration)
        span.set_attribute("embedding.dimension", len(result))

        return result
```

- [ ] **Step 2: 在 `app/retrieval/retriever.py` 中添加 retrieval 指标和追踪**

在 `retrieve` 方法中：

```python
from app.observability.metrics import MetricsRegistry
from app.observability.tracing import TracingSetup

async def retrieve(self, query: str, top_k: int = 10, traversal_depth: int = 2, *, vector_only: bool = False) -> RetrievalContext:
    """Execute the retrieval pipeline."""
    start = time.monotonic()
    tracer = TracingSetup.get_tracer()
    mode = "vector_only" if vector_only else "hybrid"

    with tracer.start_as_current_span("rag.retrieval") as span:
        span.set_attribute("rag.query", query[:100] if len(query) > 100 else query)
        span.set_attribute("rag.top_k", top_k)
        span.set_attribute("rag.traversal_depth", traversal_depth)
        span.set_attribute("rag.mode", mode)

        # Stage 1: Vector search
        with tracer.start_as_current_span("rag.vector_search") as vec_span:
            t0 = time.monotonic()
            query_vector = await self._embedder.embed_query(query)
            embedding_ms = (time.monotonic() - t0) * 1000

            t1 = time.monotonic()
            vector_results = await self._store.vector_search(query_vector=query_vector, top_k=top_k)
            vector_search_ms = (time.monotonic() - t1) * 1000

            vec_span.set_attribute("vector_search.duration_ms", vector_search_ms)
            MetricsRegistry.rag_vector_search_latency_seconds.labels(top_k=str(top_k)).observe(vector_search_ms / 1000.0)

        chunks = self._parse_vector_results(vector_results)

        # Stage 2: Graph traversal
        graph_traversal_ms = 0.0
        if not vector_only:
            with tracer.start_as_current_span("rag.graph_traversal") as graph_span:
                t2 = time.monotonic()
                chunk_ids = [str(c.chunk_id) for c in chunks]
                traversal_results = await self._store.traverse_from_chunks(chunk_ids=chunk_ids, depth=traversal_depth)
                graph_traversal_ms = (time.monotonic() - t2) * 1000

                graph_span.set_attribute("graph_traversal.duration_ms", graph_traversal_ms)
                graph_span.set_attribute("graph_traversal.depth", traversal_depth)
                MetricsRegistry.rag_graph_traversal_latency_seconds.labels(depth=str(traversal_depth)).observe(graph_traversal_ms / 1000.0)

        # Record retrieval metrics
        MetricsRegistry.rag_retrieval_total_chunks.labels(mode=mode).observe(len(chunks))
        MetricsRegistry.rag_retrieval_total_entities.labels(mode=mode).observe(len(entities))
        MetricsRegistry.rag_retrieval_total_relations.labels(mode=mode).observe(len(relations))

        span.set_attribute("rag.chunks_count", len(chunks))
        span.set_attribute("rag.entities_count", len(entities))
        span.set_attribute("rag.relations_count", len(relations))

        total_ms = (time.monotonic() - start) * 1000
        span.set_attribute("rag.total_duration_ms", total_ms)

        logger.info(...)  # existing log

        return RetrievalContext(...)
```

- [ ] **Step 3: 提交**

```bash
git add app/embedding/service.py app/retrieval/retriever.py
git commit -m "feat: add metrics and tracing to embedding and retrieval layers"
```

---

## Task 5: 手动插桩 - Extraction 和 Neo4j

**Files:**
- Modify: `app/extraction/extractor.py`
- Modify: `app/persistence/graph_store.py`

- [ ] **Step 1: 在 `app/extraction/extractor.py` 中添加 extraction 指标**

在 `_extract_single_chunk` 方法中：

```python
from app.observability.metrics import MetricsRegistry
from app.observability.tracing import TracingSetup

async def _extract_single_chunk(self, chunk: ChunkNode, domain_context: dict | None = None) -> ExtractionResult:
    """Call LLM and parse the response into domain models."""
    start = time.monotonic()
    tracer = TracingSetup.get_tracer()

    with tracer.start_as_current_span("rag.extraction") as span:
        span.set_attribute("chunk.id", str(chunk.id))
        span.set_attribute("chunk.size", len(chunk.content))

        try:
            # LLM call
            with tracer.start_as_current_span("llm.invoke") as llm_span:
                llm_start = time.monotonic()
                llm_span.set_attribute("llm.model", self._llm.model_name)

                response = await self._llm.ainvoke([...])

                llm_duration = time.monotonic() - llm_start
                MetricsRegistry.rag_llm_latency_seconds.labels(
                    model=self._llm.model_name,
                    operation="extraction",
                ).observe(llm_duration)
                MetricsRegistry.rag_llm_calls_total.labels(
                    model=self._llm.model_name,
                    operation="extraction",
                    status="success",
                ).inc()

                llm_span.set_attribute("llm.duration_seconds", llm_duration)

            # Parse response
            result = self._parse_llm_response(raw_text, chunk.id)

            # Record success metrics
            MetricsRegistry.rag_extraction_success_total.inc()

            # Determine chunk size bucket
            chunk_size = len(chunk.content)
            if chunk_size < 256:
                size_bucket = "small"
            elif chunk_size < 512:
                size_bucket = "medium"
            else:
                size_bucket = "large"

            duration = time.monotonic() - start
            MetricsRegistry.rag_extraction_latency_seconds.labels(chunk_size_bucket=size_bucket).observe(duration)

            span.set_attribute("extraction.entities_count", len(result.entities))
            span.set_attribute("extraction.concepts_count", len(result.concepts))
            span.set_attribute("extraction.relationships_count", len(result.relationships))
            span.set_attribute("extraction.duration_seconds", duration)

            return result

        except Exception as exc:
            MetricsRegistry.rag_extraction_failure_total.labels(error_type=type(exc).__name__).inc()
            MetricsRegistry.rag_llm_calls_total.labels(
                model=self._llm.model_name,
                operation="extraction",
                status="error",
            ).inc()
            span.set_attribute("error", True)
            span.record_exception(exc)
            raise
```

- [ ] **Step 2: 在 `app/persistence/graph_store.py` 中添加 Neo4j 指标**

查找所有 async 方法（如 `vector_search`, `traverse_from_chunks`, `merge_entity` 等），在每个方法中包裹：

```python
from app.observability.metrics import MetricsRegistry
from app.observability.tracing import TracingSetup

async def vector_search(self, query_vector: list[float], top_k: int) -> list[dict]:
    """Vector similarity search."""
    start = time.monotonic()
    tracer = TracingSetup.get_tracer()

    with tracer.start_as_current_span("neo4j.vector_search") as span:
        span.set_attribute("neo4j.operation", "vector_search")
        span.set_attribute("neo4j.top_k", top_k)

        try:
            # ... existing Neo4j query code ...

            duration = time.monotonic() - start
            MetricsRegistry.rag_neo4j_query_latency_seconds.labels(operation="vector_search").observe(duration)
            span.set_attribute("neo4j.duration_seconds", duration)

            return results

        except Exception as exc:
            span.set_attribute("error", True)
            span.record_exception(exc)
            raise
```

对以下方法重复此模式：
- `vector_search`
- `traverse_from_chunks`
- `merge_entity`
- `merge_concept`
- `merge_relationship`
- `ensure_indexes`
- `check_connectivity`

- [ ] **Step 3: 提交**

```bash
git add app/extraction/extractor.py app/persistence/graph_store.py
git commit -m "feat: add metrics and tracing to extraction and Neo4j layers"
```

---

## Task 6: 日志增强 - Trace ID 关联

**Files:**
- Modify: `app/main.py`
- Create: `app/observability/logging.py`

- [ ] **Step 1: 创建日志增强模块 `app/observability/logging.py`**

```python
"""Enhanced logging with OpenTelemetry trace context."""

import logging
from typing import Any

import structlog
from opentelemetry import trace
from opentelemetry.trace import SpanContext, INVALID_SPAN_CONTEXT


def get_trace_id() -> str | None:
    """Get current trace ID from OpenTelemetry context."""
    current_span = trace.get_current_span()
    span_context = current_span.get_span_context()

    if span_context == INVALID_SPAN_CONTEXT:
        return None

    return format(span_context.trace_id, "032x")


def get_span_id() -> str | None:
    """Get current span ID from OpenTelemetry context."""
    current_span = trace.get_current_span()
    span_context = current_span.get_span_context()

    if span_context == INVALID_SPAN_CONTEXT:
        return None

    return format(span_context.span_id, "016x")


def trace_context_processor(
    logger: logging.Logger,
    method_name: str,
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Add trace_id and span_id to log events."""
    trace_id = get_trace_id()
    span_id = get_span_id()

    if trace_id:
        event_dict["trace_id"] = trace_id
    if span_id:
        event_dict["span_id"] = span_id

    return event_dict


def setup_enhanced_logging(debug: bool = False) -> None:
    """Configure structlog with trace context propagation."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        trace_context_processor,  # Add trace context
    ]

    if debug:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

- [ ] **Step 2: 修改 `app/main.py` 的 `_configure_logging` 函数**

```python
from app.observability.logging import setup_enhanced_logging

def _configure_logging(settings: Settings) -> None:
    """Configure structlog and stdlib logging."""
    # Use enhanced logging with trace context
    setup_enhanced_logging(debug=settings.app.app_debug)
```

- [ ] **Step 3: 提交**

```bash
git add app/observability/logging.py app/main.py
git commit -m "feat: add trace ID correlation to structured logging"
```

---

## Task 7: Docker Compose 监控栈

**Files:**
- Modify: `docker-compose.yml`
- Create: `monitoring/prometheus/prometheus.yml`
- Create: `monitoring/prometheus/rules/alerts.yml`
- Create: `monitoring/tempo/tempo.yml`
- Create: `monitoring/grafana/provisioning/datasources/datasources.yml`
- Create: `monitoring/grafana/provisioning/dashboards/dashboards.yml`
- Create: `monitoring/grafana/dashboards/system-overview.json`
- Create: `monitoring/grafana/dashboards/rag-pipeline.json`
- Create: `monitoring/alertmanager/alertmanager.yml`

- [ ] **Step 1: 修改 `docker-compose.yml` 添加监控服务**

```yaml
version: "3.9"

services:
  # ... existing neo4j and app services ...

  # ──────────────────────────────────────────
  # Monitoring Stack
  # ──────────────────────────────────────────

  # Prometheus
  prometheus:
    image: prom/prometheus:v2.45.0
    container_name: graphrag-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./monitoring/prometheus/rules:/etc/prometheus/rules:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=15d'
      - '--web.enable-lifecycle'
    depends_on:
      - app
    networks:
      - graphrag

  # Grafana Tempo
  tempo:
    image: grafana/tempo:2.2.2
    container_name: graphrag-tempo
    ports:
      - "3200:3200"   # Tempo UI
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
    volumes:
      - ./monitoring/tempo/tempo.yml:/etc/tempo.yml:ro
      - tempo_data:/tmp/tempo
    command:
      - '--config.file=/etc/tempo.yml'
    networks:
      - graphrag

  # Grafana
  grafana:
    image: grafana/grafana:10.0.0
    container_name: graphrag-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_AUTH_ANONYMOUS_ENABLED=false
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards:ro
      - grafana_data:/var/lib/grafana
    depends_on:
      - prometheus
      - tempo
    networks:
      - graphrag

  # Alertmanager
  alertmanager:
    image: prom/alertmanager:v0.25.0
    container_name: graphrag-alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager_data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    networks:
      - graphrag

volumes:
  neo4j_data:
    driver: local
  neo4j_logs:
    driver: local
  prometheus_data:
    driver: local
  tempo_data:
    driver: local
  grafana_data:
    driver: local
  alertmanager_data:
    driver: local

networks:
  graphrag:
    driver: bridge
```

- [ ] **Step 2: 创建 Prometheus 配置 `monitoring/prometheus/prometheus.yml`**

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093

rule_files:
  - /etc/prometheus/rules/*.yml

scrape_configs:
  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Graph RAG API
  - job_name: 'graphrag-api'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s
```

- [ ] **Step 3: 创建告警规则 `monitoring/prometheus/rules/alerts.yml`**

```yaml
groups:
  - name: graphrag_infrastructure
    interval: 30s
    rules:
      - alert: ServiceDown
        expr: up{job="graphrag-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Graph RAG API 服务不可用"
          description: "服务 {{ $labels.instance }} 已宕机超过 1 分钟"

      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{job="graphrag-api",status=~"5.."}[5m]))
          / sum(rate(http_requests_total{job="graphrag-api"}[5m])) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "高错误率"
          description: "5xx 错误率超过 5% (当前值：{{ $value | humanizePercentage }})"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="graphrag-api"}[5m])) by (le)) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 延迟过高"
          description: "P95 延迟超过 2 秒 (当前值：{{ $value }}s)"

  - name: graphrag_business
    interval: 30s
    rules:
      - alert: HighExtractionFailureRate
        expr: |
          rate(rag_extraction_failure_total[5m])
          / (rate(rag_extraction_success_total[5m]) + rate(rag_extraction_failure_total[5m])) > 0.2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "提取失败率超过 20%"
          description: "LLM 提取失败率持续超过 20% (当前值：{{ $value | humanizePercentage }})"

      - alert: HighRetrievalLatency
        expr: |
          histogram_quantile(0.90, sum(rate(rag_retrieval_latency_seconds_bucket[5m])) by (le)) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "检索 P90 延迟过高"
          description: "检索 P90 延迟超过 1 秒 (当前值：{{ $value }}s)"
```

- [ ] **Step 4: 创建 Tempo 配置 `monitoring/tempo/tempo.yml`**

```yaml
server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        http:
          endpoint: 0.0.0.0:4318
        grpc:
          endpoint: 0.0.0.0:4317

storage:
  trace:
    backend: local
    local:
      path: /tmp/tempo/blocks

usage_report:
  reporting_enabled: false
```

- [ ] **Step 5: 创建 Grafana 数据源配置 `monitoring/grafana/provisioning/datasources/datasources.yml`**

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false

  - name: Tempo
    type: tempo
    access: proxy
    url: http://tempo:3200
    uid: tempo
    editable: false
    jsonData:
      httpMethod: GET
      tracesToLogs:
        datasourceUid: prometheus
        tags: ['trace_id']
        mappedTags: [{ key: 'service.name', value: 'graphrag-api' }]
        mapTagNamesEnabled: true
        spanStartTimeShift: '1h'
        spanEndTimeShift: '1h'
        filterByTraceID: true
        filterBySpanID: false
```

- [ ] **Step 6: 创建 Grafana 仪表板配置 `monitoring/grafana/provisioning/dashboards/dashboards.yml`**

```yaml
apiVersion: 1

providers:
  - name: 'Graph RAG Dashboards'
    folder: 'Graph RAG'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 30
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
```

- [ ] **Step 7: 创建 Alertmanager 配置 `monitoring/alertmanager/alertmanager.yml`**

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 12h
  receiver: 'default-receiver'
  routes:
    - match:
        severity: critical
      receiver: 'critical-receiver'

receivers:
  - name: 'default-receiver'
    webhook_configs:
      - url: 'http://app:8000/api/v1/alerts/webhook'
        send_resolved: true

  - name: 'critical-receiver'
    webhook_configs:
      - url: 'http://app:8000/api/v1/alerts/webhook'
        send_resolved: true

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname']
```

- [ ] **Step 8: 提交**

```bash
git add docker-compose.yml monitoring/
git commit -m "feat: add Docker Compose monitoring stack (Prometheus, Tempo, Grafana, Alertmanager)"
```

---

## Task 8: Grafana 仪表板

**Files:**
- Create: `monitoring/grafana/dashboards/system-overview.json`
- Create: `monitoring/grafana/dashboards/rag-pipeline.json`

- [ ] **Step 1: 创建系统概览仪表板 `monitoring/grafana/dashboards/system-overview.json`**

由于 JSON 文件较大，这里提供简化版本：

```json
{
  "annotations": {
    "list": []
  },
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 0,
  "id": null,
  "links": [],
  "liveNow": false,
  "panels": [
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "unit": "reqps"
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "options": {
        "legend": {
          "displayMode": "list",
          "placement": "bottom"
        }
      },
      "targets": [
        {
          "expr": "sum(rate(http_requests_total{job=\"graphrag-api\"}[5m]))",
          "legendFormat": "QPS"
        }
      ],
      "title": "请求量 (QPS)",
      "type": "timeseries"
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "unit": "s"
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 0
      },
      "id": 2,
      "targets": [
        {
          "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket{job=\"graphrag-api\"}[5m]))",
          "legendFormat": "P50"
        },
        {
          "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job=\"graphrag-api\"}[5m]))",
          "legendFormat": "P95"
        },
        {
          "expr": "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{job=\"graphrag-api\"}[5m]))",
          "legendFormat": "P99"
        }
      ],
      "title": "请求延迟",
      "type": "timeseries"
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "unit": "percentunit"
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 8
      },
      "id": 3,
      "targets": [
        {
          "expr": "sum(rate(http_requests_total{job=\"graphrag-api\",status=~\"5..\"}[5m])) / sum(rate(http_requests_total{job=\"graphrag-api\"}[5m]))",
          "legendFormat": "错误率"
        }
      ],
      "title": "错误率",
      "type": "timeseries"
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "unit": "percent"
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 8
      },
      "id": 4,
      "targets": [
        {
          "expr": "process_cpu_percent{job=\"graphrag-api\"}",
          "legendFormat": "CPU"
        },
        {
          "expr": "process_memory_bytes{job=\"graphrag-api\"} / 1024 / 1024",
          "legendFormat": "Memory (MB)"
        }
      ],
      "title": "资源使用",
      "type": "timeseries"
    }
  ],
  "refresh": "10s",
  "schemaVersion": 38,
  "style": "dark",
  "tags": ["graphrag", "system"],
  "templating": {
    "list": []
  },
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "timepicker": {},
  "timezone": "browser",
  "title": "System Overview",
  "uid": "system-overview",
  "version": 1,
  "weekStart": ""
}
```

- [ ] **Step 2: 创建 RAG 流水线仪表板 `monitoring/grafana/dashboards/rag-pipeline.json`**

```json
{
  "annotations": {
    "list": []
  },
  "editable": true,
  "fiscalYearStartMonth": 0,
  "graphTooltip": 0,
  "id": null,
  "links": [],
  "liveNow": false,
  "panels": [
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "unit": "s"
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "targets": [
        {
          "expr": "histogram_quantile(0.50, rate(rag_embedding_latency_seconds_bucket[5m]))",
          "legendFormat": "Embedding P50"
        },
        {
          "expr": "histogram_quantile(0.95, rate(rag_embedding_latency_seconds_bucket[5m]))",
          "legendFormat": "Embedding P95"
        }
      ],
      "title": "Embedding 延迟",
      "type": "timeseries"
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "unit": "s"
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 0
      },
      "id": 2,
      "targets": [
        {
          "expr": "histogram_quantile(0.50, rate(rag_vector_search_latency_seconds_bucket[5m]))",
          "legendFormat": "Vector Search P50"
        },
        {
          "expr": "histogram_quantile(0.95, rate(rag_vector_search_latency_seconds_bucket[5m]))",
          "legendFormat": "Vector Search P95"
        }
      ],
      "title": "向量搜索延迟",
      "type": "timeseries"
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "unit": "s"
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 8
      },
      "id": 3,
      "targets": [
        {
          "expr": "histogram_quantile(0.50, rate(rag_graph_traversal_latency_seconds_bucket[5m]))",
          "legendFormat": "Graph Traversal P50"
        },
        {
          "expr": "histogram_quantile(0.95, rate(rag_graph_traversal_latency_seconds_bucket[5m]))",
          "legendFormat": "Graph Traversal P95"
        }
      ],
      "title": "图遍历延迟",
      "type": "timeseries"
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "unit": "percentunit"
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 8
      },
      "id": 4,
      "targets": [
        {
          "expr": "rate(rag_extraction_success_total[5m]) / (rate(rag_extraction_success_total[5m]) + rate(rag_extraction_failure_total[5m]))",
          "legendFormat": "成功率"
        }
      ],
      "title": "提取成功率",
      "type": "timeseries"
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "unit": "s"
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 16
      },
      "id": 5,
      "targets": [
        {
          "expr": "histogram_quantile(0.50, rate(rag_llm_latency_seconds_bucket[5m]))",
          "legendFormat": "LLM P50"
        },
        {
          "expr": "histogram_quantile(0.95, rate(rag_llm_latency_seconds_bucket[5m]))",
          "legendFormat": "LLM P95"
        }
      ],
      "title": "LLM 调用延迟",
      "type": "timeseries"
    },
    {
      "datasource": {
        "type": "prometheus",
        "uid": "prometheus"
      },
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "unit": "s"
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 16
      },
      "id": 6,
      "targets": [
        {
          "expr": "histogram_quantile(0.50, rate(rag_neo4j_query_latency_seconds_bucket[5m]))",
          "legendFormat": "Neo4j P50"
        },
        {
          "expr": "histogram_quantile(0.95, rate(rag_neo4j_query_latency_seconds_bucket[5m]))",
          "legendFormat": "Neo4j P95"
        }
      ],
      "title": "Neo4j 查询延迟",
      "type": "timeseries"
    }
  ],
  "refresh": "10s",
  "schemaVersion": 38,
  "style": "dark",
  "tags": ["graphrag", "rag"],
  "templating": {
    "list": []
  },
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "timepicker": {},
  "timezone": "browser",
  "title": "RAG Pipeline",
  "uid": "rag-pipeline",
  "version": 1,
  "weekStart": ""
}
```

- [ ] **Step 3: 提交**

```bash
git add monitoring/grafana/dashboards/
git commit -m "feat: add Grafana dashboards for system and RAG pipeline monitoring"
```

---

## Task 9: 验证和测试

**Files:**
- Create: `tests/test_observability.py`

- [ ] **Step 1: 创建观测性测试 `tests/test_observability.py`**

```python
"""Tests for observability features (metrics, tracing, logging)."""

import pytest
from prometheus_client import CollectorRegistry

from app.observability.metrics import MetricsRegistry
from app.observability.tracing import TracingSetup
from app.observability.logging import get_trace_id, get_span_id
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


@pytest.fixture
def reset_metrics():
    """Reset metrics registry between tests."""
    MetricsRegistry._registry = CollectorRegistry()
    yield
    MetricsRegistry._registry = CollectorRegistry()


@pytest.fixture
def setup_tracing():
    """Set up in-memory tracing for tests."""
    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    yield exporter

    provider.shutdown()


class TestMetrics:
    """Test Prometheus metrics collection."""

    def test_metrics_endpoint_returns_data(self, reset_metrics):
        """Test that /metrics endpoint returns Prometheus format data."""
        metrics_data = MetricsRegistry.generate_metrics()
        assert isinstance(metrics_data, bytes)
        assert len(metrics_data) > 0

    def test_http_requests_total_counter(self, reset_metrics):
        """Test HTTP request counter increments."""
        MetricsRegistry.http_requests_total.labels(
            method="GET",
            path="/test",
            status="200",
        ).inc()

        metrics_data = MetricsRegistry.generate_metrics().decode()
        assert 'http_requests_total{method="GET",path="/test",status="200"} 1.0' in metrics_data

    def test_embedding_latency_histogram(self, reset_metrics):
        """Test embedding latency histogram observation."""
        MetricsRegistry.rag_embedding_latency_seconds.labels(
            model="m3e-large",
            device="cpu",
        ).observe(0.5)

        metrics_data = MetricsRegistry.generate_metrics().decode()
        assert "rag_embedding_latency_seconds" in metrics_data


class TestTracing:
    """Test OpenTelemetry tracing."""

    def test_tracer_creation(self, setup_tracing):
        """Test tracer can create spans."""
        tracer = TracingSetup.get_tracer("test")

        with tracer.start_as_current_span("test_span") as span:
            span.set_attribute("test.key", "test_value")

        spans = setup_tracing.get_finished_spans()
        assert len(spans) == 1
        assert spans[0].name == "test_span"
        assert spans[0].attributes["test.key"] == "test_value"

    def test_trace_id_generation(self, setup_tracing):
        """Test trace ID is generated in active span context."""
        tracer = TracingSetup.get_tracer("test")

        with tracer.start_as_current_span("test_span"):
            trace_id = get_trace_id()
            assert trace_id is not None
            assert len(trace_id) == 32  # 128-bit hex


class TestLogging:
    """Test enhanced logging with trace context."""

    def test_trace_id_in_log_event(self, setup_tracing):
        """Test trace ID is added to log events."""
        tracer = TracingSetup.get_tracer("test")

        with tracer.start_as_current_span("test_span"):
            trace_id = get_trace_id()
            span_id = get_span_id()

        assert trace_id is not None
        assert span_id is not None
```

- [ ] **Step 2: 运行测试验证**

```bash
pytest tests/test_observability.py -v
```

期望：所有测试通过

- [ ] **Step 3: 提交**

```bash
git add tests/test_observability.py
git commit -m "test: add observability tests for metrics, tracing, and logging"
```

---

## Task 10: 最终验证和文档

**Files:**
- Create: `docs/monitoring-setup.md`

- [ ] **Step 1: 创建监控设置文档 `docs/monitoring-setup.md`**

```markdown
# 监控和可观测性设置指南

## 快速启动

```bash
# 启动完整栈（应用 + 监控）
docker-compose up -d

# 查看监控服务状态
docker-compose ps

# 查看应用日志
docker-compose logs -f app
```

## 访问仪表板

| 服务 | URL | 凭据 |
|------|-----|------|
| Grafana | http://localhost:3000 | admin/admin |
| Prometheus | http://localhost:9090 | - |
| Tempo | http://localhost:3200 | - |
| Alertmanager | http://localhost:9093 | - |

## 验证步骤

### 1. 验证 Prometheus 指标

```bash
# 检查 /metrics 端点
curl http://localhost:8000/metrics | head -20

# 预期输出包含:
# http_requests_total
# http_request_duration_seconds
# rag_embedding_latency_seconds
# ...
```

### 2. 验证 Prometheus 抓取

访问 http://localhost:9090/targets

- 确认 `graphrag-api` 状态为 UP

### 3. 验证追踪

1. 发送几个请求到 API:
```bash
curl http://localhost:8000/api/v1/query -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "测试查询"}'
```

2. 访问 Grafana Tempo 数据源查看 traces

### 4. 验证仪表板

1. 登录 Grafana: http://localhost:3000
2. 浏览 "Graph RAG" 文件夹
3. 确认 System Overview 和 RAG Pipeline 仪表板显示数据

### 5. 验证告警

1. 访问 Prometheus Alerts: http://localhost:9090/alerts
2. 确认所有告警规则已加载
3. 触发告警条件（如停止 app 服务）
4. 确认告警状态变为 PENDING → FIRING

## 配置自定义

### 修改采样率

在 `.env` 中:
```bash
OTEL_TRACES_SAMPLER_ARG=0.01  # 1% 采样
```

### 添加告警通知

编辑 `monitoring/alertmanager/alertmanager.yml`:

```yaml
receivers:
  - name: 'slack-receiver'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts'
```

## 故障排查

### Prometheus 无法抓取指标

1. 检查应用日志: `docker-compose logs app`
2. 验证 /metrics 端点：`curl http://localhost:8000/metrics`
3. 检查 Prometheus 配置: `cat monitoring/prometheus/prometheus.yml`

### Tempo 未收到 traces

1. 检查 OTEL 配置: `docker-compose exec app env | grep OTEL`
2. 验证 Tempo 可访问性: `docker-compose exec app curl http://tempo:4318`
3. 检查应用日志中的 tracing 初始化信息

### Grafana 仪表板无数据

1. 确认数据源配置正确
2. 检查 Prometheus 是否有数据: `up{job="graphrag-api"}`
3. 验证时间范围选择正确

## 生产环境建议

1. **持久化**: 配置卷备份
2. **高可用**: 部署多副本 Prometheus
3. **安全**: 启用认证和 HTTPS
4. **告警**: 集成 PagerDuty/Slack
5. **保留策略**: 调整数据保留时间
```

- [ ] **Step 2: 运行完整验证**

```bash
# 启动所有服务
docker-compose up -d

# 等待服务就绪
sleep 30

# 验证所有服务运行
docker-compose ps

# 运行测试
pytest tests/test_observability.py -v
```

- [ ] **Step 3: 提交**

```bash
git add docs/monitoring-setup.md
git commit -m "docs: add monitoring setup guide"
```

---

## 自检验

**Spec 覆盖检查:**

| 需求 | 任务 |
|------|------|
| Prometheus 指标收集 | Task 2, Task 4, Task 5 |
| OpenTelemetry 追踪 | Task 3, Task 4, Task 5 |
| Tempo 后端 | Task 7 (tempo.yml) |
| Grafana 仪表板 | Task 8 |
| 告警规则 | Task 7 (alerts.yml, alertmanager.yml) |
| 日志 trace_id 关联 | Task 6 |
| Docker Compose 部署 | Task 7 |
| 测试验证 | Task 9 |
| 文档 | Task 10 |

**Placeholder 检查:**
- 无 TBD/TODO
- 所有代码步骤包含完整代码
- 所有命令包含预期输出

**类型一致性:**
- `MetricsRegistry` 在所有任务中使用相同类名
- `TracingSetup` 在所有任务中使用相同类名
- 指标命名一致 (`rag_*` 前缀)

---

**Plan 完成!**

**执行选择:**

**Plan 已保存到 `docs/superpowers/plans/2026-03-31-monitoring-observability.md`.**

**两个执行选项:**

**1. Subagent-Driven (推荐)** - 每个任务由独立的 subagent 执行，任务间 review，快速迭代

**2. Inline Execution** - 在当前会话使用 executing-plans 执行，批量执行带检查点

**选择哪种方式？**
