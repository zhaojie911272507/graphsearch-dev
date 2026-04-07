"""Prometheus metrics definitions for Graph RAG system."""

from typing import ClassVar

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    CollectorRegistry,
    generate_latest,
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
