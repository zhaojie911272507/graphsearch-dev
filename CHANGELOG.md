# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Retrieval Filtering**: Filter entities and relations by type during graph traversal
- **Relationship Deduplication**: Automatic deduplication across chunks with weight-based conflict resolution
- **Progress Callbacks**: Track extraction pipeline progress with async callbacks
- **LLM Timeout Control**: Configurable timeout for LLM requests (default 60s)
- **API Rate Limiting**: Token bucket rate limiting per IP (configurable)
- **Embedding Cache**: LRU cache for embedding vectors (default 1000 entries)
- **Webhook Support**: Async webhook notifications with HMAC signature verification
- **Slow Query Logging**: `@log_slow_query` decorator for performance monitoring
- **GraphStore Configuration**: `graph_traversal_limit` parameter for retrieval
- **Domain Module Exports**: Complete exports for temporal, domains, audit modules

### Changed
- Updated README with enterprise enhancements documentation

### Fixed
- Security validation in dynamic Cypher queries
- Import ordering in various modules

## [1.0.0] - 2025-01-15

### Added
- Initial release of GraphSearchNeo4j
- JWT authentication with RBAC
- Temporal knowledge graph
- Hybrid visualization with D3.js and Cytoscape.js
- Social simulation capabilities
- Lineage tracking
- Pipeline configuration
- Comprehensive metadata/ontology/domain management
- RAG evaluation with RAGAS

### Features
- Document ingestion pipeline (chunk, embed, extract, persist)
- Hybrid retrieval (vector Top-K + configurable graph hops)
- Streaming LLM generation
- Local M3E-Large embedding service
- Neo4j persistence with batch operations