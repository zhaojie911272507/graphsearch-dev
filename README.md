# GraphSearchNeo4j — Enterprise Graph RAG System

A production-ready **Graph Retrieval-Augmented Generation (RAG)** system combining vector search with knowledge graph traversal, powered by Neo4j, FastAPI, and local embedding models.

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

### Core Modules

| Module | Responsibility |
|---|---|
| `app/domain/` | Ontology models (Pydantic v2) — nodes, relationships, enums |
| `app/embedding/` | Local M3E-Large embedding service (singleton) |
| `app/extraction/` | LLM-based entity extraction with concurrency control |
| `app/persistence/` | Neo4j adapter with batch MERGE and vector index |
| `app/retrieval/` | Hybrid search: vector similarity + graph traversal |
| `app/api/` | FastAPI routes, dependency injection |

## Quick Start

### Prerequisites

- Python 3.13+
- Neo4j 5.x (or use Docker Compose)
- M3E-Large model files in `./model_files/embeddingmodel/m3e-large/`

### 1. Clone & Install

```bash
git clone <repo-url>
cd graphsearchneo4j-dev
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Neo4j credentials and OpenAI API key
```

### 3. Start Services (Docker)

```bash
docker-compose up -d neo4j
```

### 4. Run the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Open API Docs

Navigate to `http://localhost:8000/docs` for Swagger UI.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/ingest` | Ingest a document (chunk → embed → extract → persist) |
| `POST` | `/api/v1/query` | Query with hybrid retrieval + streaming LLM answer |
| `GET` | `/health` | System health check |

## Full Docker Deployment

```bash
# Build and start everything (Neo4j + App)
docker-compose up --build -d
```

Ensure the M3E-Large model is available at `./model_files/embeddingmodel/m3e-large/` — it will be mounted as a read-only volume.

## Testing

```bash
pytest --cov=app --cov-report=html tests/
```

## Project Structure

```
graphsearchneo4j-dev/
├── app/
│   ├── main.py              # FastAPI app + lifespan
│   ├── config.py             # pydantic-settings
│   ├── exceptions.py         # Custom exception hierarchy
│   ├── domain/               # Ontology models
│   │   ├── enums.py
│   │   ├── nodes.py
│   │   ├── relationships.py
│   │   └── schemas.py
│   ├── embedding/            # Local embedding service
│   │   └── service.py
│   ├── extraction/           # LLM extraction pipeline
│   │   ├── chunker.py
│   │   ├── extractor.py
│   │   └── prompts.py
│   ├── persistence/          # Neo4j adapter
│   │   └── graph_store.py
│   ├── retrieval/            # Hybrid search engine
│   │   └── retriever.py
│   └── api/                  # FastAPI routes + DI
│       ├── dependencies.py
│       └── routes/
│           ├── ingest.py
│           └── query.py
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── pyproject.toml
```
