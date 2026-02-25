Project Structure Overview
The entire Graph RAG system has been scaffolded as a production-ready, modular Python application. Here's what each module delivers:
1. app/config.py — Configuration
pydantic-settings based configuration with environment variable loading
Aggregated Settings class with sub-configs for Neo4j, OpenAI, Embedding, Retrieval, Extraction
Validation on URI schemes, model paths, numeric bounds
2. app/domain/ — Core Ontology Models
Enums: NodeType, EntityType, RelationType — strict enumerations for the graph schema
Nodes: DocumentNode, ChunkNode, EntityNode, ConceptNode — all frozen Pydantic models with neo4j_properties() serialization
Relationships: GraphRelationship with self-loop prevention, weight bounds [0.0, 1.0]
Schemas: IngestRequest/Response, QueryRequest/Response, RetrievalContext with formatted_context property
Embedding dimension validation (1024 for M3E-Large) on ChunkNode
3. app/embedding/service.py — Local M3E-Large Service
Thread-safe singleton pattern via __new__ + threading.Lock
Lazy model loading via load_model() during startup
Async-safe via asyncio.to_thread (won't block the event loop)
embed_documents() (batch) and embed_query() (single) interfaces
Runtime dimension validation on every output vector
4. app/extraction/ — LLM Extraction Pipeline
TextChunker: Sliding window with configurable size/overlap
GraphExtractor: Full LLM pipeline with asyncio.Semaphore concurrency control
Retry strategy: tenacity (1 initial + 2 retries) with exponential backoff
Graceful degradation: Returns empty ExtractionResult on exhausted retries
Strict JSON Mode output parsing into typed domain objects
5. app/persistence/graph_store.py — Neo4j Adapter
Async context manager (__aenter__/__aexit__) for connection lifecycle
Batch MERGE via UNWIND for both nodes and relationships (never single inserts)
Typed Cypher templates per NodeType and RelationType
Vector index creation (CREATE VECTOR INDEX IF NOT EXISTS) for Chunk embeddings
vector_search() using db.index.vector.queryNodes
traverse_from_chunks() for 1-N hop graph expansion
6. app/retrieval/retriever.py — Hybrid Search
Stage 1: Embed query → vector similarity search → Top-K Chunks
Stage 2: Graph traversal from seed chunks → Entities & Concepts
Stage 3: Context assembly into RetrievalContext with formatted text
7. app/api/ — FastAPI Layer
Dependencies: Type-annotated Depends factories for all services
POST /api/v1/ingest: Full pipeline — chunk → embed → extract → persist
POST /api/v1/query: Hybrid retrieval → SSE streaming LLM generation
GET /health: System health (Neo4j + Embedding model status)
CORS middleware, structured error responses
8. Infrastructure
Dockerfile: Multi-stage build (base → deps → production), non-root user
docker-compose.yml: Neo4j 5 Community + App with volume mounts, health checks
.env.example: All configurable environment variables documented
9. Tests
Shared fixtures in conftest.py (mock services, sample domain objects)
Domain model tests (nodes, relationships, schemas — validation, serialization)
Extraction tests (JSON parsing, edge cases, graceful degradation)
Chunker tests (empty text, overlap, sequential indexing)
Next Steps
cp .env.example .env and fill in your credentials
pip install -r requirements.txt to install dependencies
docker-compose up -d neo4j to start Neo4j
uvicorn app.main:app --reload to launch the API
Open http://localhost:8000/docs for the Swagger UI