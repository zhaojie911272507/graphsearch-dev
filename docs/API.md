# API Reference

This document provides a quick reference for the main API endpoints.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

### POST /api/v1/auth/login
Login and receive JWT token.

**Request:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

## Documents

### POST /api/v1/documents/upload
Upload a document for processing.

### GET /api/v1/documents
List all documents.

### DELETE /api/v1/documents/{id}
Delete a document.

## Ingestion

### POST /api/v1/ingest
Trigger the full ingestion pipeline for a document.

**Request:**
```json
{
  "document_id": "uuid",
  "domain_key": "default"
}
```

## Query

### POST /api/v1/query
Execute a hybrid query with streaming response.

**Request:**
```json
{
  "question": "What is Graph RAG?",
  "top_k": 10,
  "traversal_depth": 2,
  "entity_types": ["Person", "Organization"],
  "relation_types": ["KNOWS", "WORKS_AT"]
}
```

**Response:** Server-Sent Events (SSE) stream

## Metadata

### GET /api/v1/metadata/assets
Search and filter assets.

### GET /api/v1/metadata/nodes/{id}
Get node details.

## Ontology

### GET /api/v1/ontology/entity-types
List all entity types.

### POST /api/v1/ontology/entity-types
Create a new entity type.

### GET /api/v1/ontology/relation-types
List all relation types.

## Domains

### GET /api/v1/domains
List all domains.

### POST /api/v1/domains
Create a new domain.

### POST /api/v1/domains/{id}/activate
Activate a domain.

## Evaluation

### GET /api/v1/evaluation/metrics
Get evaluation metrics (RAGAS).

### POST /api/v1/evaluation/run
Run evaluation on queries.

## Temporal

### GET /api/v1/temporal/entity/{id}/history
Get entity version history.

### GET /api/v1/temporal/summary
Get global temporal summary.

## Simulation

### POST /api/v1/simulation/setup
Setup a simulation.

### POST /api/v1/simulation/exec/run
Run a simulation.

### GET /api/v1/simulation/reports
Get simulation reports.

## Webhook

### POST /webhook (internal)
Receive webhook notifications (configured in settings).

## Health

### GET /health
Check system health.

### GET /metrics
Get Prometheus metrics.