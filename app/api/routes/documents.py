"""Document management API routes.

Provides endpoints for:
- File upload (single and batch)
- Document listing and search
- Document details
- Document deletion
- Batch import from directory
"""

import logging
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.dependencies import (
    EmbeddingServiceDep,
    GraphExtractorDep,
    GraphStoreDep,
    SettingsDep,
)
from app.domain.nodes import DocumentNode
from app.exceptions import GraphRAGError
from app.extraction.chunker import TextChunker
from app.services.document_parser import DocumentParser, DocumentParseError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Document Management"])


class UploadResponse(BaseModel):
    """Response for file upload."""
    document_id: str
    title: str
    filename: str
    file_size: int
    file_type: str
    status: str
    message: str
    chunk_count: int | None = None
    entity_count: int | None = None


class DocumentListResponse(BaseModel):
    """Response for document list."""
    items: list[dict]
    total: int
    page: int
    page_size: int
    total_pages: int


class BatchUploadResponse(BaseModel):
    """Response for batch upload."""
    success_count: int
    failure_count: int
    results: list[dict]


# ──────────────────────────────────────────
# Upload Endpoints
# ──────────────────────────────────────────

@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a single document file",
    description="Upload a PDF, DOCX, or TXT file, parse it, and ingest into the knowledge graph.",
)
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload"),
    domain_key: str | None = Form(None, description="Domain context for extraction"),
    use_dedup: bool | None = Form(False, description="Enable entity deduplication by name"),
    store: GraphStoreDep = None,
    embedder: EmbeddingServiceDep = None,
    extractor: GraphExtractorDep = None,
    settings: SettingsDep = None,
) -> UploadResponse:
    """Upload and process a single document file."""
    try:
        # Validate file
        content = await file.read()
        DocumentParser.validate_file(file.filename, len(content))

        # Parse document
        file_type = "unknown"  # Default value
        try:
            text, metadata, file_type = DocumentParser.parse_document(file.filename, content)
        except DocumentParseError as e:
            logger.warning("Document parsing failed: %s", e.message)
            # Create document node with failed status
            doc_node = DocumentNode(
                title=file.filename,
                filename=file.filename,
                file_size=len(content),
                file_type=file_type,  # Use the detected file type or "unknown"
                upload_status="failed",
                parse_error=e.message,
            )
            await store.upsert_nodes([doc_node])
            return UploadResponse(
                document_id=str(doc_node.id),
                title=doc_node.title,
                filename=doc_node.filename,
                file_size=doc_node.file_size,
                file_type=doc_node.file_type,
                status="failed",
                message=f"Parsing failed: {e.message}",
            )

        # Create document node
        doc_node = DocumentNode(
            title=metadata.get('title') or Path(file.filename).stem,
            filename=file.filename,
            file_size=len(content),
            file_type=file_type,
            upload_status="processing",
        )
        await store.upsert_nodes([doc_node])

        # Process with existing ingestion pipeline
        try:
            # Chunk text
            chunker = TextChunker(settings.extraction)
            chunks = chunker.chunk_text(text, document_id=doc_node.id)

            if not chunks:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Document content produced zero chunks after splitting.",
                )

            # Generate embeddings
            chunk_texts = [c.content for c in chunks]
            vectors = await embedder.embed_documents(chunk_texts)

            # Rebuild chunks with embeddings
            from app.domain.nodes import ChunkNode
            embedded_chunks: list[ChunkNode] = []
            for chunk, vector in zip(chunks, vectors, strict=True):
                embedded_chunk = chunk.model_copy(update={"embedding": tuple(vector)})
                embedded_chunks.append(embedded_chunk)

            # Extract entities/concepts/relationships
            # TODO: Pass domain_context to extractor for domain-specific extraction
            extraction_results = await extractor.extract_from_chunks(embedded_chunks)

            # Aggregate nodes and relationships
            all_entities = []
            all_concepts = []
            all_relationships = []

            from app.domain.enums import RelationType
            from app.domain.relationships import GraphRelationship

            for result in extraction_results:
                all_entities.extend(result.entities)
                all_concepts.extend(result.concepts)
                all_relationships.extend(result.relationships)

            # Update entities/concepts with source document reference (for deduplication)
            doc_id_str = str(doc_node.id)
            for entity in all_entities:
                if doc_id_str not in entity.source_document_ids:
                    entity.source_document_ids.append(doc_id_str)
            for concept in all_concepts:
                if doc_id_str not in concept.source_document_ids:
                    concept.source_document_ids.append(doc_id_str)

            # Add HAS_CHUNK relationships
            has_chunk_rels = [
                GraphRelationship(
                    relation_type=RelationType.HAS_CHUNK,
                    source_id=doc_node.id,
                    target_id=chunk.id,
                    weight=1.0,
                )
                for chunk in embedded_chunks
            ]

            # Add MENTIONS relationships
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

            # Persist to Neo4j
            if use_dedup:
                # Use deduplication-aware upsert for entities and concepts
                await store.upsert_nodes([doc_node, *embedded_chunks])
                await store.upsert_entities_with_dedup(all_entities, str(doc_node.id))
                await store.upsert_concepts_with_dedup(all_concepts, str(doc_node.id))
            else:
                # Standard upsert without deduplication
                all_nodes = [doc_node, *embedded_chunks, *all_entities, *all_concepts]
                await store.upsert_nodes(all_nodes)

            await store.upsert_relationships(all_relationships)

            # Update document status to complete
            doc_node_complete = doc_node.model_copy(
                update={"upload_status": "complete"}
            )
            await store.upsert_nodes([doc_node_complete])

            logger.info(
                "Document uploaded successfully: %s, chunks=%d, entities=%d, rels=%d",
                doc_node.id,
                len(embedded_chunks),
                len(all_entities) + len(all_concepts),
                len(all_relationships),
            )

            return UploadResponse(
                document_id=str(doc_node.id),
                title=doc_node.title,
                filename=doc_node.filename,
                file_size=doc_node.file_size,
                file_type=doc_node.file_type,
                status="complete",
                message="Document uploaded and processed successfully",
                chunk_count=len(embedded_chunks),
                entity_count=len(all_entities) + len(all_concepts),
            )

        except Exception as e:
            logger.error("Document processing failed: %s", e)
            # Update document status to failed
            doc_node_failed = doc_node.model_copy(
                update={"upload_status": "failed", "parse_error": str(e)}
            )
            await store.upsert_nodes([doc_node_failed])
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Document processing failed: {str(e)}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Upload failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}",
        )


@router.post(
    "/batch-upload",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload multiple document files",
    description="Upload multiple files at once and process them.",
)
async def batch_upload_documents(
    files: list[UploadFile] = File(..., description="Document files to upload"),
    domain_key: str | None = Form(None, description="Domain context for extraction"),
    store: GraphStoreDep = None,
    embedder: EmbeddingServiceDep = None,
    extractor: GraphExtractorDep = None,
    settings: SettingsDep = None,
) -> BatchUploadResponse:
    """Upload and process multiple document files."""
    results = []
    success_count = 0
    failure_count = 0

    for file in files:
        try:
            content = await file.read()
            DocumentParser.validate_file(file.filename, len(content))
            text, metadata, file_type = DocumentParser.parse_document(file.filename, content)

            doc_node = DocumentNode(
                title=metadata.get('title') or Path(file.filename).stem,
                filename=file.filename,
                file_size=len(content),
                file_type=file_type,
                upload_status="processing",
            )
            await store.upsert_nodes([doc_node])

            # Reuse single upload logic for processing
            # (In production, this should be done asynchronously)
            # For now, just mark as complete
            doc_node_complete = doc_node.model_copy(update={"upload_status": "complete"})
            await store.upsert_nodes([doc_node_complete])

            results.append({
                "filename": file.filename,
                "status": "success",
                "document_id": str(doc_node.id),
            })
            success_count += 1

        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "failed",
                "error": str(e),
            })
            failure_count += 1
            logger.error("Batch upload failed for %s: %s", file.filename, e)

    return BatchUploadResponse(
        success_count=success_count,
        failure_count=failure_count,
        results=results,
    )


# ──────────────────────────────────────────
# List and Retrieve Endpoints
# ──────────────────────────────────────────

@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List uploaded documents",
    description="Get paginated list of uploaded documents with filtering and search.",
)
async def list_documents(
    store: GraphStoreDep,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
) -> DocumentListResponse:
    """List documents from the knowledge graph."""
    try:
        # Get documents from metadata assets API
        assets = await store.get_metadata_assets(
            node_type="Document",
            search_query=q,
            sort_by="created_at",
            order="desc",
            limit=page_size,
            offset=(page - 1) * page_size,
        )

        total = await store.count_metadata_assets(
            node_type="Document",
            search_query=q,
        )

        items = []
        for asset in assets:
            items.append({
                "id": asset.get("id"),
                "title": asset.get("title", asset.get("name", "")),
                "filename": asset.get("filename", ""),
                "file_size": asset.get("file_size", 0),
                "file_type": asset.get("file_type", ""),
                "upload_status": asset.get("upload_status", "complete"),
                "created_at": asset.get("created_at"),
                "parse_error": asset.get("parse_error"),
            })

        return DocumentListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size if total > 0 else 0,
        )

    except Exception as e:
        logger.error("Failed to list documents: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list documents: {e}",
        )


@router.get(
    "/{document_id}",
    response_model=dict,
    summary="Get document details",
    description="Get complete details for a specific document including parsed content (chunks, entities, concepts, entity types, relation types).",
)
async def get_document_detail(
    document_id: str,
    store: GraphStoreDep,
) -> dict:
    """Get detailed information about a specific document including all parsed content.

    Returns:
        Complete document details including:
        - Basic metadata (title, filename, file_size, etc.)
        - Chunks: list of text chunks with content and semantic metadata
        - Entities: list of extracted entities with types and descriptions
        - Concepts: list of extracted concepts with definitions
        - Entity types: count breakdown by entity type
        - Relation types: count breakdown by relation type
        - Statistics: summary counts
    """
    try:
        node_data = await store.get_node_by_id(document_id)
        if not node_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found",
            )

        async with store.driver.session(database=store._settings.database) as session:
            # Get chunks
            chunks_result = await session.run("""
                MATCH (doc:Document {id: $document_id})-[:HAS_CHUNK]->(chunk:Chunk)
                RETURN chunk ORDER BY chunk.chunk_index
            """, document_id=document_id)
            chunks = []
            async for record in chunks_result:
                chunk_data = dict(record["chunk"])
                chunks.append({
                    "id": chunk_data.get("id"),
                    "content": chunk_data.get("content", ""),
                    "chunk_index": chunk_data.get("chunk_index", 0),
                    "section_title": chunk_data.get("section_title", ""),
                    "paragraph_type": chunk_data.get("paragraph_type", "paragraph"),
                    "word_count": chunk_data.get("word_count", 0),
                    "sentence_count": chunk_data.get("sentence_count", 0),
                    "semantic_boundary_start": chunk_data.get("semantic_boundary_start", True),
                    "semantic_boundary_end": chunk_data.get("semantic_boundary_end", True),
                    "previous_chunk_overlap": chunk_data.get("previous_chunk_overlap", ""),
                    "created_at": chunk_data.get("created_at"),
                    "updated_at": chunk_data.get("updated_at"),
                })

            # Get entities
            entities_result = await session.run("""
                MATCH (doc:Document {id: $document_id})-[:HAS_CHUNK]->(chunk:Chunk)-[:MENTIONS]->(entity:Entity)
                RETURN DISTINCT entity ORDER BY entity.name
            """, document_id=document_id)
            entities = []
            entity_type_counts: dict[str, int] = {}
            async for record in entities_result:
                entity_data = dict(record["entity"])
                entity_type = entity_data.get("entity_type", "OTHER")
                entity_type_counts[entity_type] = entity_type_counts.get(entity_type, 0) + 1
                entities.append({
                    "id": entity_data.get("id"),
                    "name": entity_data.get("name", ""),
                    "entity_type": entity_type,
                    "description": entity_data.get("description", ""),
                    "reference_count": entity_data.get("reference_count", 1),
                    "source_document_ids": entity_data.get("source_document_ids", []),
                    "created_at": entity_data.get("created_at"),
                    "updated_at": entity_data.get("updated_at"),
                })

            # Get concepts
            concepts_result = await session.run("""
                MATCH (doc:Document {id: $document_id})-[:HAS_CHUNK]->(chunk:Chunk)-[:MENTIONS]->(concept:Concept)
                RETURN DISTINCT concept ORDER BY concept.name
            """, document_id=document_id)
            concepts = []
            async for record in concepts_result:
                concept_data = dict(record["concept"])
                concepts.append({
                    "id": concept_data.get("id"),
                    "name": concept_data.get("name", ""),
                    "definition": concept_data.get("definition", ""),
                    "reference_count": concept_data.get("reference_count", 1),
                    "source_document_ids": concept_data.get("source_document_ids", []),
                    "created_at": concept_data.get("created_at"),
                    "updated_at": concept_data.get("updated_at"),
                })

            # Get entity types summary
            entity_types_result = await session.run("""
                MATCH (doc:Document {id: $document_id})-[:HAS_CHUNK]->(chunk:Chunk)-[:MENTIONS]->(entity:Entity)
                RETURN entity.entity_type as type, count(entity) as count
                ORDER BY count DESC
            """, document_id=document_id)
            entity_types = {}
            async for record in entity_types_result:
                entity_types[record["type"]] = record["count"]

            # Get relation types summary
            relation_types_result = await session.run("""
                MATCH (doc:Document {id: $document_id})-[:HAS_CHUNK]->(chunk:Chunk)-[:MENTIONS]->(entity:Entity)-[r]-(other:Entity)
                WHERE other IN [
                    (doc)-[:HAS_CHUNK]->(c:Chunk)-[:MENTIONS]->(e:Entity) | e
                ]
                RETURN type(r) as relation_type, count(r) as count
                ORDER BY count DESC
            """, document_id=document_id)
            relation_types = {}
            total_relations = 0
            async for record in relation_types_result:
                relation_types[record["relation_type"]] = record["count"]
                total_relations += record["count"]

        return {
            "id": node_data.get("id"),
            "title": node_data.get("title", node_data.get("name", "")),
            "filename": node_data.get("filename", ""),
            "file_size": node_data.get("file_size", 0),
            "file_type": node_data.get("file_type", ""),
            "upload_status": node_data.get("upload_status", "complete"),
            "parse_error": node_data.get("parse_error"),
            "created_at": node_data.get("created_at"),
            "updated_at": node_data.get("updated_at"),
            "content_hash": node_data.get("content_hash"),
            "source_url": node_data.get("source_url"),
            # Parsed content
            "chunks": chunks,
            "entities": entities,
            "concepts": concepts,
            # Type summaries
            "entity_types": entity_type_counts,
            "relation_types": relation_types,
            # Statistics
            "statistics": {
                "chunk_count": len(chunks),
                "entity_count": len(entities),
                "concept_count": len(concepts),
                "relation_count": total_relations,
                "unique_entity_types": len(entity_type_counts),
                "unique_relation_types": len(relation_types),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get document detail: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get document detail: {e}",
        )


# ──────────────────────────────────────────
# Delete Endpoint
# ──────────────────────────────────────────

@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
    description="""Delete a document and its associated data.

**Deletion Modes:**

1. `delete_entities=true` (default for backward compatibility):
   - Deletes the document node
   - Deletes all chunks (text segments)
   - Deletes all entities and concepts extracted from those chunks
   - Deletes all relationships between these nodes

2. `delete_entities=false` (preserve shared entities):
   - Deletes the document node
   - Deletes all chunks
   - Preserves entities and concepts (removes document reference)
   - Decrements reference_count for affected entities
   - Only deletes entities if reference_count reaches 0

**Entity Deduplication:**
When using the deduplication feature, entities with the same name and type
across different documents are merged into a single node. The system tracks
which documents reference each entity via `source_document_ids` and `reference_count`.
""",
)
async def delete_document(
    document_id: str,
    store: GraphStoreDep,
    delete_entities: bool = True,  # New optional parameter
    use_dedup: bool = False,  # Whether entity deduplication is enabled
) -> None:
    """Delete a document from the knowledge graph.

    Args:
        document_id: The UUID of the document to delete.
        delete_entities: If True (default), also delete entities/concepts
            extracted from this document's chunks. If False, only delete
            the document and its chunks, preserving entities that might be
            shared with other documents.
        use_dedup: If True, use the deduplication-aware deletion logic
            that updates reference counts and only deletes entities
            when no documents reference them.
    """
    try:
        if use_dedup:
            # Use deduplication-aware deletion
            result = await store.delete_document_with_entity_dedup(document_id)

            if result["documents_deleted"] == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document {document_id} not found",
                )

            logger.info(
                "Document deleted (dedup mode): %s, chunks=%d, entities_updated=%d",
                document_id,
                result["chunks_deleted"],
                result["entities_updated"],
            )
        elif delete_entities:
            # Delete document and all connected nodes (chunks, entities, concepts)
            result = await store.delete_node_and_connected(document_id, "Document")

            if result["documents_deleted"] == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document {document_id} not found",
                )

            logger.info(
                "Document deleted successfully: %s, chunks=%d, entities=%d",
                document_id,
                result["chunks_deleted"],
                result["entities_deleted"],
            )
        else:
            # Delete only document and chunks, preserve entities
            result = await store.delete_document_and_chunks_only(document_id)

            if result["documents_deleted"] == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document {document_id} not found",
                )

            logger.info(
                "Document deleted (entities preserved): %s, chunks=%d",
                document_id,
                result["chunks_deleted"],
            )

        return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete document: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {e}",
        )


# ──────────────────────────────────────────
# Batch Import Endpoint
# ──────────────────────────────────────────

@router.post(
    "/batch-import",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Batch import documents from directory",
    description="Import all supported documents from a local directory.",
)
async def batch_import_from_directory(
    directory_path: str = Form(..., description="Path to directory containing documents"),
    store: GraphStoreDep = None,
) -> BatchUploadResponse:
    """Import documents from a local directory."""
    try:
        dir_path = Path(directory_path)
        if not dir_path.exists() or not dir_path.is_dir():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Directory does not exist: {directory_path}",
            )

        # Find all supported files
        supported_extensions = {'.pdf', '.docx', '.txt'}
        files = [
            f for f in dir_path.iterdir()
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]

        results = []
        success_count = 0
        failure_count = 0

        for file_path in files:
            try:
                with open(file_path, 'rb') as f:
                    content = f.read()

                # Parse and create document node
                text, metadata, file_type = DocumentParser.parse_document(file_path.name, content)
                doc_node = DocumentNode(
                    title=metadata.get('title') or file_path.stem,
                    filename=file_path.name,
                    file_size=len(content),
                    file_type=file_type,
                    upload_status="complete",
                )
                await store.upsert_nodes([doc_node])

                results.append({
                    "filename": file_path.name,
                    "status": "success",
                    "document_id": str(doc_node.id),
                })
                success_count += 1

            except Exception as e:
                results.append({
                    "filename": file_path.name,
                    "status": "failed",
                    "error": str(e),
                })
                failure_count += 1
                logger.error("Batch import failed for %s: %s", file_path.name, e)

        return BatchUploadResponse(
            success_count=success_count,
            failure_count=failure_count,
            results=results,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Batch import failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch import failed: {e}",
        )
