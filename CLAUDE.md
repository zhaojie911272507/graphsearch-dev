# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚀 Quick Start Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start Neo4j (requires Docker)
docker-compose up -d neo4j

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest --cov=app --cov-report=html tests/

# Type checking
mypy app/

# Linting (format + lint)
ruff check app/
ruff format app/
```

## 🏗️ Architecture Overview

This is an enterprise **Graph RAG (Retrieval-Augmented Generation)** system combining vector search with knowledge graph traversal, powered by Neo4j, FastAPI, and local embedding models.

### Core Pipeline

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  FastAPI     │────▶│  Extraction      │────▶│  Neo4j          │
│  (API Layer) │     │  Pipeline        │     │  (Graph Store)  │
└──────┬───────┘     └──────────────────┘     └────────┬────────┘
       │                                                │
       ▼                                                ▼
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Query       │────▶│  Hybrid          │────▶│  LLM Generation │
│  Endpoint    │     │  Retrieval       │     │  (Streaming)    │
└──────────────┘     └──────────────────┘     └─────────────────┘
```

### Module Responsibilities

| Module | Key Files | Responsibility |
|---|---|---|
| `app/domain/` | `nodes.py`, `relationships.py`, `enums.py`, `schemas.py` | **Ontology models** (Pydantic v2) — immutable, frozen dataclasses with `neo4j_properties()` serialization |
| `app/embedding/` | `service.py` | **Local M3E-Large embedding** (singleton, thread-safe, async via `asyncio.to_thread`) |
| `app/extraction/` | `extractor.py`, `chunker.py`, `prompts.py` | **LLM-based entity extraction** with concurrency control (semaphore), retry logic (tenacity), graceful degradation |
| `app/persistence/` | `graph_store.py` | **Neo4j adapter** with async context manager, batch MERGE via UNWIND, vector index management |
| `app/retrieval/` | `retriever.py` | **Hybrid search**: vector similarity (Top-K chunks) + graph traversal (N-hop expansion) → context assembly |
| `app/visualization/` | `routes.py`, `schemas.py` | **Graph visualization API** for D3.js frontend (nodes/edges, stats) |
| `app/api/routes/` | `metadata.py`, `ontology.py`, `intelligence.py`, `evaluation.py` | **Extended APIs**: asset catalog, ontology CRUD, community review queue, evaluation metrics (RAGAS) |

### Key Design Patterns

1. **Thread-safe singleton** — `EmbeddingService` uses `__new__` + `threading.Lock`
2. **Application lifecycle** — `main.py:lifespan` initializes heavy services at startup, cleans up at shutdown
3. **Dependency injection** — FastAPI `Depends` for services (`GraphStoreDep`, `EmbeddingServiceDep`)
4. **Error handling** — Hierarchical exception classes in `exceptions.py` (base `GraphRAGError`)
5. **Configuration** — `pydantic-settings` with `BaseSettings`, validated at startup
6. **Type safety** — Strict type hints throughout, `mypy` config with `strict=true`

## 📝 Configuration

Environment variables (copy from `.env.example`):

```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# Embedding
EMBEDDING_MODEL_PATH=./model_files/embeddingmodel/m3e-large
EMBEDDING_DIMENSION=1024
EMBEDDING_DEVICE=cpu
```

Required: M3E-Large model files at `./model_files/embeddingmodel/m3e-large/`

## 📦 Frontend

React + TypeScript SPA served at `/viz/`:

```
frontend/
├── src/pages/
│   ├── AssetCatalog.tsx      # Browse/search assets
│   ├── NodeDetail.tsx        # Node detail view
│   ├── OntologyManager.tsx   # EntityType/RelationType CRUD
│   ├── ReviewQueue.tsx       # Community review workflow
│   ├── Explorations.tsx      # Save/share exploration paths
│   └── EvaluationDashboard.tsx # RAGAS metrics dashboard
```

Build & serve:

```bash
cd frontend
npm install
npm run dev  # Vite dev server
npm run build  # Production build
```

## ⚙️ Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_graph_store_indexes.py

# Coverage
pytest --cov=app --cov-report=html tests/
open htmlcov/index.html

# Async tests
pytest --asyncio-mode=auto
```

Test structure:

- `tests/conftest.py` — shared fixtures (mock services, sample domain objects)
- Domain model validation tests (nodes, relationships, schemas)
- Extraction pipeline tests (JSON parsing, edge cases)
- Persistence layer tests (Cypher queries, index creation)

## 🔧 Development Notes

- **Python 3.13+** required
- All domain models are **frozen** (immutable) — use `.model_copy(update={...})` for updates
- Vector dimension is **1024** for M3E-Large — validated in `ChunkNode` and `EmbeddingService`
- LLM extraction uses **JSON mode** (`response_format: {type: "json_object"}`)
- Graph traversal depth is configurable (default 2 hops) — see `RetrievalSettings.graph_traversal_depth`
- Batch operations use **UNWIND** in Cypher for performance (never single inserts)
- **Graceful degradation** — extraction returns empty result on exhausted retries rather than failing the entire pipeline

## 📚 Additional Documentation

- `docs/prd.md` — Original product requirements
- `docs/projectstructure.md` — Detailed module breakdown
- `docs/final-implementation-plan.md` — Extended platform features (metadata management, community intelligence, evaluation)
- `docs/metadata-management-prd.md` — Metadata module PRD

## 🔌 Cursor Rules

- `no-commit-attribution.mdc` — Do not add `Made-with: Cursor` or `Co-authored-by` trailers to git commits
- `no-xiaohongshu-emojis.mdc` — Avoid excessive emoji in code/comments (use sparingly)
