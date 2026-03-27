# GraphSearchNeo4j — Enterprise Graph RAG System

A production-ready **Graph Retrieval-Augmented Generation (RAG)** stack: vector search plus knowledge-graph traversal in **Neo4j**, **FastAPI** (async), local **M3E-Large** embeddings, and **LLM** extraction and answering. The same service also exposes **metadata / ontology / domain** management, **document** upload and parsing, **audit** logging, **collective intelligence** and **evaluation** APIs, and an optional **social simulation** subsystem (setup, dialogue, execution, reports).

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  FastAPI      │────▶│  Extraction      │────▶│  Neo4j          │
│  (API Layer)  │     │  Pipeline        │     │  (Graph Store)  │
└──────┬───────┘     └──────────────────┘     └────────┬────────┘
       │                                                │
       ▼                                                ▼
┌──────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Query       │────▶│  Hybrid          │────▶│  LLM Generation │
│  Endpoint    │     │  Retrieval       │     │  (Streaming)    │
└──────────────┘     └──────────────────┘     └─────────────────┘
```

Platform features (domains, documents, simulation, viz) sit alongside the core ingest/query path and share the same graph and services.

### Core Modules

| Module | Responsibility |
|--------|------------------|
| `app/domain/` | Ontology and graph domain models (Pydantic v2), including `domain/social/` for simulation |
| `app/embedding/` | Local M3E-Large embedding service (singleton, thread-safe) |
| `app/extraction/` | LLM-based chunking and entity extraction (concurrency, retries) |
| `app/persistence/` | Neo4j adapter: batch MERGE, vector indexes, audit log helpers |
| `app/retrieval/` | Hybrid retrieval: vector Top-K + configurable graph hops |
| `app/services/` | Document parsing, simulation orchestration, reports, ontology helpers, etc. |
| `app/api/` | FastAPI routers under `/api/v1`, schemas, dependencies |
| `app/visualization/` | Built-in D3-style graph UI served at `/viz/` |
| `app/evaluation/` | RAG evaluation metrics and dataset helpers |

## Quick Start

### Prerequisites

- Python 3.13+
- Neo4j 5.x (Docker Compose is supported)
- M3E-Large weights under `./model_files/embeddingmodel/m3e-large/` (see `.gitignore`; not committed)

### 1. Clone and install

```bash
git clone <repo-url>
cd graphsearchneo4j-dev
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment

```bash
cp .env.example .env
```

Edit `.env`: Neo4j credentials, `OPENAI_*` for extraction/query, embedding paths, and optional `SIMULATION_*` tunables (see `.env.example`).

### 3. Neo4j (Docker)

```bash
docker-compose up -d neo4j
```

### 4. Run the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Root `/` redirects to **`/viz/`** (bundled visualization SPA)

### 5. Frontend (optional dev server)

The production build can be copied into `app/visualization/static/` for `/viz/`. For local UI development:

```bash
cd frontend
npm install
npm run dev
```

Configure the Vite dev server proxy to the API if you call backends from the SPA (see `frontend/vite.config.ts`).

## API Overview

All JSON APIs below are under the **`/api/v1`** prefix unless noted.

| Area | Prefix (after `/api/v1`) | Description |
|------|---------------------------|-------------|
| Ingestion | `/ingest` | Document ingest: chunk, embed, extract, persist |
| Query | `/query` | Hybrid retrieval + streaming LLM answer |
| Metadata | `/metadata` | Asset / catalog style metadata |
| Ontology | `/ontology` | Entity and relation type management |
| Domains | `/domains` | Domain lifecycle; optional default domain bootstrap |
| Documents | `/documents` | Document upload, listing, parsed content |
| Intelligence | `/intelligence` | Community / review-style intelligence APIs |
| Evaluation | `/evaluation` | RAG evaluation and monitoring |
| Audit | `/audit` | Audit log access |
| Simulation | `/simulation`, `/simulation/dialogue`, `/simulation/reports` | Social simulation setup, runs, dialogue, reports |
| System | `/health` | Health (Neo4j + embedding readiness) |

Use `/docs` for the authoritative operation list and request bodies.

## Full Docker deployment

```bash
docker-compose up --build -d
```

Mount or place the M3E-Large model at `./model_files/embeddingmodel/m3e-large/` so the container can load embeddings.

## Testing

```bash
pytest --cov=app --cov-report=html tests/
```

Focused examples:

```bash
pytest tests/test_extraction/test_chunker.py -q
pytest tests/test_simulation_setup.py -q
```

## Documentation

Additional design and runbooks live under `docs/`, for example:

- `docs/PLATFORM_GUIDE.md` — platform usage
- `docs/SOCIAL_SIMULATION_ENV_SETUP.md` — simulation configuration
- `docs/ChunkNode.md`, `docs/ENTITY_DEDUPLICATION.md` — graph / extraction notes

## Project structure (high level)

```
graphsearchneo4j-dev/
├── app/
│   ├── main.py                 # App factory, lifespan, route mounting
│   ├── config.py               # pydantic-settings
│   ├── exceptions.py
│   ├── domain/                 # Core + social simulation models
│   ├── embedding/
│   ├── extraction/
│   ├── persistence/            # graph_store, audit_log, ...
│   ├── retrieval/
│   ├── services/               # document_parser, simulation_*, ...
│   ├── evaluation/
│   ├── visualization/          # API + static SPA for /viz/
│   └── api/
│       ├── dependencies.py
│       ├── schemas/
│       └── routes/             # ingest, query, metadata, ontology, ...
├── frontend/                   # React + TypeScript (Vite)
├── tests/
├── scripts/                    # fixtures / API smoke helpers
├── test_business_files/        # Sample documents (optional local tests)
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── pyproject.toml
```

## License

See `LICENSE`.
