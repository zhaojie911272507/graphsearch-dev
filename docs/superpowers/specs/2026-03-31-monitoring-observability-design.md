# 监控和可观测性设计文档

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

## 1. 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                           │
│  ┌─────────────┐  ┌─────────────────┐  ┌──────────────────────┐    │
│  │ HTTP Request│  │  Business Logic │  │  Neo4j / LLM Calls   │    │
│  │  Middleware │  │  (Retriever,    │  │  (External Services) │    │
│  │  (OTel)     │  │   Extractor)    │  │                      │    │
│  └──────┬──────┘  └────────┬────────┘  └──────────┬───────────┘    │
│         │                  │                       │                │
│         ▼                  ▼                       ▼                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              OpenTelemetry Trace Pipeline                    │   │
│  │  • Auto-instrumentation (FastAPI, HTTPX)                     │   │
│  │  • Manual spans (embedding, retrieval, extraction)           │   │
│  │  • Context propagation (trace_id → logs)                     │   │
│  └─────────────────────────────┬───────────────────────────────┘   │
│                                │ OTLP HTTP                          │
└────────────────────────────────┼────────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   Grafana Tempo        │
                    │   (Trace Storage)      │
                    └───────────┬────────────┘
                                │
                    ┌───────────▼────────────┐
                    │   Grafana Dashboard    │
                    │   (Unified UI)         │
                    └────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      Prometheus Stack                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────────┐  │
│  │   Prometheus    │  │  Alertmanager   │  │   Pushgateway      │  │
│  │   (Metrics)     │  │  (Alerts)       │  │   (Optional)       │  │
│  └────────┬────────┘  └────────┬────────┘  └────────────────────┘  │
│           │                    │                                    │
│           │   Pull /metrics    │   Push alerts                      │
│           ▼                    ▼                                    │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    Grafana Dashboard                            │ │
│  │  • System metrics (CPU, memory, request latency)               │ │
│  │  • RAG business metrics (retrieval latency, success rate)      │ │
│  │  • Alert status panel                                           │ │
│  └────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

## 2. 指标设计

### 2.1 系统指标（自动收集）
| 指标名 | 类型 | 标签 | 描述 |
|--------|------|------|------|
| `http_requests_total` | Counter | method, path, status | HTTP 请求总数 |
| `http_request_duration_seconds` | Histogram | method, path | HTTP 请求延迟分布 |
| `http_requests_in_progress` | Gauge | - | 当前进行中的请求数 |
| `process_cpu_percent` | Gauge | - | Python 进程 CPU 使用率 |
| `process_memory_bytes` | Gauge | type (rss/vms) | Python 进程内存使用 |

### 2.2 RAG 业务指标（手动插桩）
| 指标名 | 类型 | 标签 | 描述 |
|--------|------|------|------|
| `rag_embedding_latency_seconds` | Histogram | model, device | Embedding 生成延迟 |
| `rag_vector_search_latency_seconds` | Histogram | top_k | 向量搜索延迟 |
| `rag_graph_traversal_latency_seconds` | Histogram | depth | 图遍历延迟 |
| `rag_retrieval_total_chunks` | Histogram | mode (vector_only/hybrid) | 检索返回的 chunk 数量 |
| `rag_extraction_latency_seconds` | Histogram | chunk_size, retry_count | LLM 提取延迟 |
| `rag_extraction_success_total` | Counter | - | 提取成功次数 |
| `rag_extraction_failure_total` | Counter | error_type | 提取失败次数 |
| `rag_llm_latency_seconds` | Histogram | model, operation | LLM API 调用延迟 |
| `rag_neo4j_query_latency_seconds` | Histogram | operation | Neo4j 查询延迟 |
| `rag_neo4j_connection_pool_size` | Gauge | state (active/idle) | Neo4j 连接池状态 |

## 3. 追踪设计

### 3.1 Span 层级结构
```
HTTP Request (fastapi.request)
├── Authentication/Validation
├── Retrieval Pipeline (rag.retrieval)
│   ├── Embedding Generation (rag.embedding)
│   ├── Vector Search (rag.vector_search)
│   └── Graph Traversal (rag.graph_traversal)
│       ├── Entity Expansion
│       └── Relationship Expansion
├── LLM Extraction (rag.extraction)
│   ├── LLM API Call (llm.invoke)
│   └── Response Parsing
└── Response Serialization
```

### 3.2 自定义 Span 属性
- `rag.query_type`: 查询类型（keyword/semantic/hybrid）
- `rag.retrieval_mode`: 检索模式（vector_only/hybrid）
- `rag.chunk_count`: 返回的 chunk 数量
- `rag.entity_count`: 返回的 entity 数量
- `rag.llm.model`: 使用的 LLM 模型
- `rag.embedding.model`: 使用的 embedding 模型
- `error.type`: 错误类型（如果发生错误）

## 4. 日志增强

### 4.1 日志字段增强
所有日志记录必须包含以下字段：
- `trace_id`: OpenTelemetry trace ID（如果存在）
- `span_id`: 当前 span ID
- `service_name`: 服务名称（graphrag-api）
- `request_id`: 唯一请求 ID
- `duration_ms`: 操作耗时（对于完成日志）

### 4.2 关键日志点
1. **请求开始**: `Incoming request method=POST path=/api/v1/query trace_id=xxx`
2. **检索完成**: `Retrieval completed chunks=5 entities=3 relations=2 duration_ms=150.5`
3. **提取完成**: `Extraction completed chunk_id=xxx entities=2 concepts=1 relationships=3 duration_ms=800.2`
4. **错误日志**: `Error during retrieval error_type=Neo4jError trace_id=xxx duration_ms=50.1`

## 5. 告警规则

### 5.1 基础告警
```yaml
groups:
  - name: graphrag_infrastructure
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "高错误率：{{ $value | humanizePercentage }}"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 延迟过高：{{ $value }}s"

      - alert: ServiceDown
        expr: up{job="graphrag-api"} == 0
        for: 1m
        labels:
          severity: critical
```

### 5.2 业务告警
```yaml
  - name: graphrag_business
    interval: 30s
    rules:
      - alert: HighExtractionFailureRate
        expr: rate(rag_extraction_failure_total[5m]) / (rate(rag_extraction_success_total[5m]) + rate(rag_extraction_failure_total[5m])) > 0.2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "提取失败率超过 20%"

      - alert: Neo4jConnectionPoolExhausted
        expr: rag_neo4j_connection_pool_size{state="active"} > 0.9 * rag_neo4j_connection_pool_size{state="total"}
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Neo4j 连接池接近耗尽"
```

## 6. Grafana 仪表板

### 6.1 Dashboard 1: System Overview
- 请求量时间序列（QPS）
- P50/P95/P99 延迟时间序列
- 错误率时间序列
- CPU/内存使用率
- 服务健康状态

### 6.2 Dashboard 2: RAG Pipeline
- 检索各阶段延迟分布（Embedding/Vector Search/Graph Traversal）
- 检索返回结果数量分布（Chunks/Entities/Relations）
- LLM 提取成功率
- 检索模式分布（Vector Only vs Hybrid）

### 6.3 Dashboard 3: Trace Explorer
- Tempo 数据源集成的 Trace 列表
- 慢查询 Trace 排行榜
- 错误 Trace 排行榜

## 7. Docker Compose 部署

新增服务：
```yaml
services:
  # 新增：Prometheus
  prometheus:
    image: prom/prometheus:v2.45.0
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/prometheus/rules:/etc/prometheus/rules
      - prometheus_data:/prometheus

  # 新增：Tempo
  tempo:
    image: grafana/tempo:2.2.2
    ports:
      - "3200:3200"
      - "4317:4317"  # OTLP gRPC
      - "4318:4318"  # OTLP HTTP
    volumes:
      - ./monitoring/tempo/tempo.yml:/etc/tempo.yml
      - tempo_data:/tmp/tempo

  # 新增：Grafana
  grafana:
    image: grafana/grafana:10.0.0
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
      - grafana_data:/var/lib/grafana

  # 新增：Alertmanager
  alertmanager:
    image: prom/alertmanager:v0.25.0
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml
```

## 8. 接口变更

### 8.1 新增端点
- `GET /metrics`: Prometheus 指标暴露端点（端口 8000）
- `GET /healthz`: 增强健康检查（包含依赖服务详细状态）

### 8.2 健康检查增强
```json
{
  "status": "ok",
  "neo4j_connected": true,
  "embedding_model_loaded": true,
  "details": {
    "neo4j": {
      "pool_size": 50,
      "active_connections": 3,
      "last_health_check": "2026-03-31T10:00:00Z"
    },
    "embedding": {
      "model_path": "./model_files/embeddingmodel/m3e-large",
      "device": "cpu",
      "dimension": 1024
    }
  }
}
```

## 9. 配置变更

### 9.1 新增环境变量
```bash
# Observability
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4318
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1
OTEL_SERVICE_NAME=graphrag-api
OTEL_RESOURCE_ATTRIBUTES=deployment.environment=development

# Metrics
METRICS_ENABLED=true
METRICS_PORT=8000

# Alerting
ALERTMANAGER_URL=http://alertmanager:9093
WEBHOOK_ALERT_URL=http://internal-monitoring/webhook
```

## 10. 验收标准

1. **指标收集**:
   - [ ] `/metrics` 端点返回 Prometheus 格式指标
   - [ ] Prometheus 成功抓取指标
   - [ ] 所有定义的系统和业务指标都存在

2. **分布式追踪**:
   - [ ] 每个 HTTP 请求生成 trace
   - [ ] trace 包含完整的 span 层级
   - [ ] 在 Grafana 中可以查看和搜索 trace

3. **日志关联**:
   - [ ] 日志包含 trace_id 字段
   - [ ] 可以通过 trace_id 关联日志和追踪

4. **告警**:
   - [ ] 告警规则正确加载到 Prometheus
   - [ ] 触发告警时 Alertmanager 收到通知

5. **可视化**:
   - [ ] Grafana 仪表板显示系统和 RAG 指标
   - [ ] 仪表板自动刷新数据

6. **部署**:
   - [ ] Docker Compose 成功启动所有监控服务
   - [ ] 服务间网络连通正常
