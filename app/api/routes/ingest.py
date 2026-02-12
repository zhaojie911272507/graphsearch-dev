"""Document ingestion endpoint.

POST /ingest — Accepts raw document text, triggers the full pipeline:
  1. Text chunking
  2. Embedding generation
  3. LLM entity/concept extraction
  4. Neo4j persistence (nodes + relationships)
"""

import hashlib
import logging
import time

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.api.dependencies import (
    EmbeddingServiceDep,
    GraphExtractorDep,
    GraphStoreDep,
    SettingsDep,
)
from app.domain.enums import RelationType
from app.domain.nodes import ChunkNode, DocumentNode
from app.domain.relationships import GraphRelationship
from app.domain.schemas import IngestRequest, IngestResponse
from app.exceptions import GraphRAGError
from app.extraction.chunker import TextChunker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post(
    "",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a document",
    description="Parse, chunk, embed, extract entities, and persist to the graph.",
)
async def ingest_document(
    request: IngestRequest,
    settings: SettingsDep,
    store: GraphStoreDep,
    embedder: EmbeddingServiceDep,
    extractor: GraphExtractorDep,
    background_tasks: BackgroundTasks,
) -> IngestResponse:
    """Full synchronous ingestion pipeline.

    For very large documents, consider moving heavy steps to
    BackgroundTasks or a task queue (Celery / ARQ).
    """
    start = time.monotonic()

    try:
        # 1. Create document node
        content_hash = hashlib.sha256(request.content.encode()).hexdigest()
        doc_node = DocumentNode(
            title=request.title,
            source_url=request.source_url,
            content_hash=content_hash,
        )

        # 2. Chunk text
        chunker = TextChunker(settings.extraction)
        chunks = chunker.chunk_text(request.content, document_id=doc_node.id)

        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Document content produced zero chunks after splitting.",
            )

        # 3. Generate embeddings
        chunk_texts = [c.content for c in chunks]
        vectors = await embedder.embed_documents(chunk_texts)

        # Rebuild chunks with embeddings
        embedded_chunks: list[ChunkNode] = []
        for chunk, vector in zip(chunks, vectors, strict=True):
            embedded_chunk = chunk.model_copy(
                update={"embedding": tuple(vector)}
            )
            embedded_chunks.append(embedded_chunk)

        # 4. Extract entities/concepts/relationships via LLM
        extraction_results = await extractor.extract_from_chunks(embedded_chunks)

        # 5. Aggregate all nodes and relationships
        all_entities = []
        all_concepts = []
        all_relationships: list[GraphRelationship] = []

        for result in extraction_results:
            all_entities.extend(result.entities)
            all_concepts.extend(result.concepts)
            all_relationships.extend(result.relationships)

        # Add HAS_CHUNK relationships (Document -> Chunk)
        has_chunk_rels = [
            GraphRelationship(
                relation_type=RelationType.HAS_CHUNK,
                source_id=doc_node.id,
                target_id=chunk.id,
                weight=1.0,
            )
            for chunk in embedded_chunks
        ]

        # Add MENTIONS relationships (Chunk -> Entity)
        mentions_rels: list[GraphRelationship] = []
        for result in extraction_results:
            chunk_id = result.chunk_id
            for entity in result.entities:
                mentions_rels.append(
                    GraphRelationship(
                        relation_type=RelationType.MENTIONS,
                        source_id=chunk_id,
                        target_id=entity.id,
                        weight=0.8,
                    )
                )

        all_relationships.extend(has_chunk_rels)
        all_relationships.extend(mentions_rels)

        # 6. Persist to Neo4j (batch writes)
        all_nodes = [doc_node, *embedded_chunks, *all_entities, *all_concepts]
        await store.upsert_nodes(all_nodes)
        await store.upsert_relationships(all_relationships)

        elapsed = (time.monotonic() - start) * 1000
        logger.info(
            "Ingestion completed in %.1fms: doc=%s, chunks=%d, entities=%d, rels=%d",
            elapsed,
            doc_node.id,
            len(embedded_chunks),
            len(all_entities) + len(all_concepts),
            len(all_relationships),
        )

        return IngestResponse(
            document_id=doc_node.id,
            chunk_count=len(embedded_chunks),
            entity_count=len(all_entities) + len(all_concepts),
            relationship_count=len(all_relationships),
            message=f"Document '{request.title}' ingested successfully in {elapsed:.0f}ms",
        )

    except HTTPException:
        raise
    except GraphRAGError as exc:
        logger.error("Ingestion failed: %s", exc.message, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion pipeline error: {exc.message}",
        ) from exc
    except Exception as exc:
        logger.error("Unexpected ingestion error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during ingestion.",
        ) from exc
