"""Hybrid retrieval engine combining vector search with graph traversal.

Implements the multi-stage retrieval strategy:
1. Vector search → Top-K Chunks
2. Graph traversal → Related Entities & Concepts (1-2 hops)
3. Context assembly → Formatted text for LLM generation
"""

import logging
import time
from uuid import UUID

from app.domain.enums import EntityType, RelationType
from app.domain.schemas import (
    RetrievalContext,
    RetrievedChunk,
    RetrievedEntity,
    RetrievedRelation,
)
from app.embedding.service import EmbeddingService
from app.persistence.graph_store import GraphStore

logger = logging.getLogger(__name__)


class GraphRetriever:
    """Multi-stage hybrid retriever: vector search + graph traversal.

    Args:
        graph_store: Neo4j persistence adapter.
        embedding_service: Local embedding service for query vectorization.
    """

    def __init__(
        self,
        graph_store: GraphStore,
        embedding_service: EmbeddingService,
    ) -> None:
        self._store = graph_store
        self._embedder = embedding_service

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        traversal_depth: int = 2,
        *,
        vector_only: bool = False,
        entity_types: list[str] | None = None,
        relation_types: list[str] | None = None,
        min_entity_score: float | None = None,
    ) -> RetrievalContext:
        """Execute the retrieval pipeline.

        Args:
            query: Natural language query string.
            top_k: Number of chunks from vector search.
            traversal_depth: Graph traversal hops from seed chunks.
            vector_only: If True, skip graph traversal (baseline mode).
            entity_types: Filter entities by type during traversal.
            relation_types: Filter relations by type during traversal.
            min_entity_score: Minimum score threshold for entity filtering.

        Returns:
            Assembled RetrievalContext with chunks and optionally entities/relations.
        """
        start = time.monotonic()

        # Stage 1: Vector search
        t0 = time.monotonic()
        query_vector = await self._embedder.embed_query(query)
        embedding_ms = (time.monotonic() - t0) * 1000

        t1 = time.monotonic()
        vector_results = await self._store.vector_search(
            query_vector=query_vector,
            top_k=top_k,
        )
        vector_search_ms = (time.monotonic() - t1) * 1000

        chunks = self._parse_vector_results(vector_results)

        if not chunks:
            logger.info("Vector search returned no results for query: %s", query[:100])
            return RetrievalContext()

        entities: list[RetrievedEntity] = []
        relations: list[RetrievedRelation] = []
        graph_traversal_ms = 0.0

        # Stage 2: Graph traversal (skipped in vector_only mode)
        if not vector_only:
            chunk_ids = [str(c.chunk_id) for c in chunks]
            t2 = time.monotonic()
            traversal_results = await self._store.traverse_from_chunks(
                chunk_ids=chunk_ids,
                depth=traversal_depth,
                entity_types=entity_types,
                relation_types=relation_types,
            )
            graph_traversal_ms = (time.monotonic() - t2) * 1000
            entities, relations = self._parse_traversal_results(
                traversal_results,
                min_score=min_entity_score,
            )

        total_ms = (time.monotonic() - start) * 1000
        logger.info(
            "Retrieval completed in %.1fms (embed=%.1f, vec=%.1f, graph=%.1f): "
            "%d chunks, %d entities, %d relations [mode=%s]",
            total_ms,
            embedding_ms,
            vector_search_ms,
            graph_traversal_ms,
            len(chunks),
            len(entities),
            len(relations),
            "vector_only" if vector_only else "hybrid",
        )

        return RetrievalContext(
            chunks=chunks,
            entities=entities,
            relations=relations,
        )

    def _parse_vector_results(
        self,
        records: list[dict[str, object]],
    ) -> list[RetrievedChunk]:
        """Convert Neo4j vector search records to RetrievedChunk models."""
        chunks: list[RetrievedChunk] = []

        for record in records:
            node = record.get("node")
            score = record.get("score", 0.0)

            if not isinstance(node, dict):
                # neo4j driver returns Node objects — extract properties
                try:
                    node_props: dict[str, object] = dict(node)  # type: ignore[arg-type]
                except (TypeError, ValueError):
                    logger.warning("Skipping unparseable vector result")
                    continue
            else:
                node_props = node

            try:
                chunk = RetrievedChunk(
                    chunk_id=UUID(str(node_props.get("id", ""))),
                    content=str(node_props.get("content", "")),
                    score=float(score),  # type: ignore[arg-type]
                    document_title=str(node_props.get("document_title", "")),
                    chunk_index=int(node_props.get("chunk_index", 0)),  # type: ignore[arg-type]
                )
                chunks.append(chunk)
            except (ValueError, TypeError) as exc:
                logger.warning("Failed to parse vector result: %s", exc)
                continue

        return chunks

    def _parse_traversal_results(
        self,
        records: list[dict[str, object]],
        min_score: float | None = None,
    ) -> tuple[list[RetrievedEntity], list[RetrievedRelation]]:
        """Convert Neo4j traversal records to domain models.

        Args:
            records: List of traversal result records from Neo4j.
            min_score: Minimum score threshold for entity filtering (not currently
                available in traversal results, but reserved for future use).

        Returns:
            Tuple of (entities, relations) parsed from the records.
        """
        entities: list[RetrievedEntity] = []
        relations: list[RetrievedRelation] = []
        seen_entity_ids: set[str] = set()

        for record in records:
            neighbor = record.get("neighbor")
            rels = record.get("rels", [])

            # Parse neighbor node
            if neighbor is not None:
                try:
                    neighbor_props: dict[str, object] = dict(neighbor)  # type: ignore[arg-type]
                except (TypeError, ValueError):
                    continue

                node_id = str(neighbor_props.get("id", ""))
                if node_id in seen_entity_ids:
                    continue
                seen_entity_ids.add(node_id)

                entity_type_str = str(neighbor_props.get("entity_type", "OTHER"))
                try:
                    entity_type = EntityType(entity_type_str)
                except ValueError:
                    entity_type = EntityType.OTHER

                try:
                    entities.append(
                        RetrievedEntity(
                            entity_id=UUID(node_id),
                            name=str(neighbor_props.get("name", "")),
                            entity_type=entity_type,
                        )
                    )
                except (ValueError, TypeError):
                    continue

            # Parse relationships
            if isinstance(rels, list):
                for rel in rels:
                    try:
                        rel_props: dict[str, object] = dict(rel)  # type: ignore[arg-type]
                    except (TypeError, ValueError):
                        continue

                    try:
                        rel_type = RelationType(
                            str(rel_props.get("relation_type", "RELATED_TO"))
                        )
                    except ValueError:
                        rel_type = RelationType.RELATED_TO

                    relations.append(
                        RetrievedRelation(
                            source_name=str(rel_props.get("source_name", "unknown")),
                            target_name=str(rel_props.get("target_name", "unknown")),
                            relation_type=rel_type,
                            weight=float(rel_props.get("weight", 0.5)),  # type: ignore[arg-type]
                        )
                    )

        # Apply minimum score filter if specified (placeholder for future implementation)
        if min_score is not None and min_score > 0:
            logger.debug(
                "min_entity_score filter specified (%.2f) but score is not available "
                "in traversal results - skipping filter",
                min_score,
            )

        return entities, relations
