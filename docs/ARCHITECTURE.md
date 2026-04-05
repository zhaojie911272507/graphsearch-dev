# Architecture Documentation

## Overview

GraphSearchNeo4j is an enterprise-grade Graph RAG (Retrieval-Augmented Generation) system that combines vector search with knowledge graph traversal, powered by Neo4j, FastAPI, and local embedding models.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Frontend (React + TypeScript)               │
│                         served at /viz/ (SPA)                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Application                           │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    Middleware Layer                               │  │
│  │  - CORS Middleware                                               │  │
│  │  - Rate Limiting (Token Bucket)                                  │  │
│  │  - Authentication (JWT)                                         │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                      API Routes                                 │  │
│  │  /auth, /ingest, /query, /metadata, /ontology, /domains,        │  │
│  │  /documents, /intelligence, /evaluation, /audit, /temporal,    │  │
│  │  /simulation, /lineage                                           │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
         ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
         │   Retrieval  │ │  Extraction   │ │  Visualization│
         │   Pipeline   │ │   Pipeline   │ │    Routes    │
         └──────┬───────┘ └──────┬───────┘ └──────────────┘
                │                │
                ▼                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           Service Layer                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │  GraphStore  │ │   Embedding  │ │  Webhook     │ │   Metrics    │   │
│  │  (Neo4j)     │ │   Service    │ │   Service    │ │   Registry   │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. API Layer (`app/api/`)

- **Routes**: FastAPI routers for all endpoints
- **Schemas**: Pydantic models for request/response validation
- **Dependencies**: Dependency injection for services

### 2. Domain Layer (`app/domain/`)

- **Nodes**: Graph node models (Document, Chunk, Entity, Concept, Agent, Memory, etc.)
- **Relationships**: Graph relationship models
- **Enums**: Type definitions (NodeType, EntityType, RelationType)
- **Schemas**: API request/response schemas

### 3. Extraction Pipeline (`app/extraction/`)

1. **Chunker**: Split documents into chunks (fixed/recursive strategies)
2. **Extractor**: LLM-based entity/relationship extraction with:
   - Concurrency control (Semaphore)
   - Retry logic (exponential backoff)
   - Progress callbacks
   - Relationship deduplication
   - Timeout control

### 4. Retrieval Pipeline (`app/retrieval/`)

1. **Vector Search**: Embed query, search similar chunks
2. **Graph Traversal**: Expand from chunks to entities/concepts
3. **Filtering**: Entity type, relation type filtering
4. **Context Assembly**: Format results for LLM

### 5. Persistence Layer (`app/persistence/`)

- **GraphStore**: Neo4j async adapter
  - Batch operations (UNWIND)
  - Vector indexes
  - Temporal versioning
  - Audit logging
- **TemporalStore**: Entity version management

### 6. Embedding Service (`app/embedding/`)

- Singleton pattern (thread-safe)
- LRU caching
- Local M3E-Large model
- Async support via `asyncio.to_thread`

### 7. Observability (`app/observability/`)

- Structured logging (structlog)
- Prometheus metrics
- OpenTelemetry tracing
- Slow query logging decorator

## Data Flow

### Document Ingestion

```
Document → Chunking → Embedding → Extraction → Neo4j Storage
                                         │
                                         ▼
                                  Webhook Notification
                                  (if configured)
```

### Query Processing

```
User Query → Embedding → Vector Search → Graph Traversal → 
                                              │
                                              ▼
Context Assembly → LLM Generation → Streaming Response
```

## Configuration

All configuration is managed through Pydantic Settings:

| Setting | Environment Variable | Description |
|---------|---------------------|-------------|
| Neo4j | `NEO4J_*` | Database connection |
| OpenAI | `OPENAI_*` | LLM API configuration |
| Retrieval | `RETRIEVAL_*` | Top-K, traversal depth |
| Extraction | `EXTRACTION_*` | Concurrency, retries, timeout |
| Rate Limiting | `RATE_LIMIT_*` | Requests per minute, burst |
| Embedding Cache | `EMBEDDING_CACHE_*` | Enabled, max size |
| Webhook | `WEBHOOK_*` | URL, secret, timeout |
| Observability | `LOG_SLOW_*`, `SLOW_QUERY_*` | Logging configuration |

## Security

- JWT authentication with RBAC (admin/reviewer/user)
- Password hashing (bcrypt)
- Rate limiting per IP
- Parameterized Cypher queries (no SQL injection)

## Performance

- Async/await throughout
- Connection pooling (Neo4j)
- Embedding LRU cache
- Batch operations (UNWIND)
- Concurrent chunk processing

## Testing

- Unit tests for domain models
- Integration tests for API endpoints
- Async test support (pytest-asyncio)
- Mock fixtures (pytest-mock)

## Deployment

- Docker Compose for development
- Single Dockerfile for production
- Health check endpoints
- Graceful shutdown