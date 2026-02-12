"""Neo4j Graph Store adapter.

Provides a high-level async interface for batch node/relationship
persistence with MERGE-based idempotency and vector index management.
"""

import logging
from types import TracebackType
from typing import Self

from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncManagedTransaction

from app.config import Neo4jSettings
from app.domain.enums import NodeType, RelationType
from app.domain.nodes import GraphNode
from app.domain.relationships import GraphRelationship
from app.exceptions import Neo4jConnectionError, Neo4jQueryError, Neo4jTransactionError

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────
# Cypher Templates
# ──────────────────────────────────────────

_MERGE_DOCUMENT = """
UNWIND $batch AS row
MERGE (n:Document {id: row.id})
SET n += row
"""

_MERGE_CHUNK = """
UNWIND $batch AS row
MERGE (n:Chunk {id: row.id})
SET n += row
"""

_MERGE_ENTITY = """
UNWIND $batch AS row
MERGE (n:Entity {id: row.id})
SET n += row
"""

_MERGE_CONCEPT = """
UNWIND $batch AS row
MERGE (n:Concept {id: row.id})
SET n += row
"""

_MERGE_RELATIONSHIP = """
UNWIND $batch AS row
MATCH (source {id: row.source_id})
MATCH (target {id: row.target_id})
CALL apoc.merge.relationship(source, row.relation_type, {id: row.id}, row, target) YIELD rel
RETURN count(rel)
"""

_MERGE_RELATIONSHIP_TYPED: dict[RelationType, str] = {
    RelationType.HAS_CHUNK: """
        UNWIND $batch AS row
        MATCH (source {id: row.source_id})
        MATCH (target {id: row.target_id})
        MERGE (source)-[r:HAS_CHUNK {id: row.id}]->(target)
        SET r.weight = row.weight, r.relation_type = row.relation_type
    """,
    RelationType.MENTIONS: """
        UNWIND $batch AS row
        MATCH (source {id: row.source_id})
        MATCH (target {id: row.target_id})
        MERGE (source)-[r:MENTIONS {id: row.id}]->(target)
        SET r.weight = row.weight, r.relation_type = row.relation_type
    """,
    RelationType.RELATED_TO: """
        UNWIND $batch AS row
        MATCH (source {id: row.source_id})
        MATCH (target {id: row.target_id})
        MERGE (source)-[r:RELATED_TO {id: row.id}]->(target)
        SET r.weight = row.weight, r.relation_type = row.relation_type
    """,
    RelationType.BELONGS_TO: """
        UNWIND $batch AS row
        MATCH (source {id: row.source_id})
        MATCH (target {id: row.target_id})
        MERGE (source)-[r:BELONGS_TO {id: row.id}]->(target)
        SET r.weight = row.weight, r.relation_type = row.relation_type
    """,
    RelationType.DEFINES: """
        UNWIND $batch AS row
        MATCH (source {id: row.source_id})
        MATCH (target {id: row.target_id})
        MERGE (source)-[r:DEFINES {id: row.id}]->(target)
        SET r.weight = row.weight, r.relation_type = row.relation_type
    """,
}

_NODE_MERGE_MAP: dict[NodeType, str] = {
    NodeType.DOCUMENT: _MERGE_DOCUMENT,
    NodeType.CHUNK: _MERGE_CHUNK,
    NodeType.ENTITY: _MERGE_ENTITY,
    NodeType.CONCEPT: _MERGE_CONCEPT,
}

_CREATE_VECTOR_INDEX = """
CREATE VECTOR INDEX chunk_embedding_index IF NOT EXISTS
FOR (c:Chunk)
ON (c.embedding)
OPTIONS {
    indexConfig: {
        `vector.dimensions`: $dimension,
        `vector.similarity_function`: 'cosine'
    }
}
"""

_VECTOR_SEARCH = """
CALL db.index.vector.queryNodes('chunk_embedding_index', $top_k, $query_vector)
YIELD node, score
RETURN node, score
"""

_GRAPH_TRAVERSAL = """
MATCH (start:Chunk)
WHERE start.id IN $chunk_ids
CALL {
    WITH start
    MATCH path = (start)-[*1..$depth]-(neighbor)
    WHERE neighbor:Entity OR neighbor:Concept
    RETURN neighbor, relationships(path) AS rels
    LIMIT 50
}
RETURN DISTINCT neighbor, rels
"""


class GraphStore:
    """Async Neo4j graph store with connection lifecycle management.

    Usage:
        async with GraphStore(settings) as store:
            await store.upsert_nodes(nodes)

    Args:
        settings: Neo4j connection configuration.
    """

    def __init__(self, settings: Neo4jSettings) -> None:
        self._settings = settings
        self._driver: AsyncDriver | None = None

    async def __aenter__(self) -> Self:
        """Open the Neo4j driver connection pool."""
        try:
            driver = AsyncGraphDatabase.driver(
                self._settings.uri,
                auth=(self._settings.username, self._settings.password),
            )
            await driver.verify_connectivity()
            self._driver = driver
            logger.info(
                "Neo4j connection established",
                extra={"uri": self._settings.uri, "database": self._settings.database},
            )
        except Exception as exc:
            raise Neo4jConnectionError(
                f"Failed to connect to Neo4j: {exc}",
                details={"uri": self._settings.uri},
            ) from exc
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Close the Neo4j driver."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")

    @property
    def driver(self) -> AsyncDriver:
        """Access the underlying driver, raising if not connected."""
        if self._driver is None:
            raise Neo4jConnectionError("GraphStore is not connected. Use 'async with' context.")
        return self._driver

    # ──────────────────────────────────────────
    # Schema & Index Management
    # ──────────────────────────────────────────

    async def ensure_indexes(self, dimension: int = 1024) -> None:
        """Create vector index and uniqueness constraints if they don't exist.

        Args:
            dimension: Embedding vector dimension (default 1024 for M3E-Large).
        """
        async with self.driver.session(database=self._settings.database) as session:
            try:
                # Uniqueness constraints on node IDs
                for label in NodeType:
                    await session.run(
                        f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{label.value}) "
                        f"REQUIRE n.id IS UNIQUE"
                    )
                # Vector index for Chunk embeddings
                await session.run(_CREATE_VECTOR_INDEX, dimension=dimension)
                logger.info(
                    "Indexes and constraints ensured",
                    extra={"dimension": dimension},
                )
            except Exception as exc:
                raise Neo4jQueryError(
                    f"Failed to create indexes: {exc}",
                    details={"dimension": dimension},
                ) from exc

    # ──────────────────────────────────────────
    # Batch Node Operations
    # ──────────────────────────────────────────

    async def upsert_nodes(self, nodes: list[GraphNode]) -> int:
        """Batch upsert nodes using MERGE (idempotent).

        Nodes are grouped by type and written in a single transaction
        per type using UNWIND for high throughput.

        Args:
            nodes: List of graph nodes to persist.

        Returns:
            Total number of nodes processed.
        """
        if not nodes:
            return 0

        # Group by node type
        grouped: dict[NodeType, list[dict[str, object]]] = {}
        for node in nodes:
            props = node.neo4j_properties()
            grouped.setdefault(node.node_type, []).append(props)

        total = 0
        async with self.driver.session(database=self._settings.database) as session:
            for node_type, batch in grouped.items():
                cypher = _NODE_MERGE_MAP.get(node_type)
                if cypher is None:
                    logger.warning("No MERGE template for node type: %s", node_type)
                    continue
                try:
                    await session.execute_write(
                        self._run_batch_write, cypher, batch
                    )
                    total += len(batch)
                    logger.debug(
                        "Upserted %d %s nodes", len(batch), node_type.value
                    )
                except Exception as exc:
                    raise Neo4jTransactionError(
                        f"Failed to upsert {node_type.value} nodes: {exc}",
                        details={"node_type": node_type.value, "batch_size": len(batch)},
                    ) from exc

        return total

    # ──────────────────────────────────────────
    # Batch Relationship Operations
    # ──────────────────────────────────────────

    async def upsert_relationships(self, relationships: list[GraphRelationship]) -> int:
        """Batch upsert relationships using typed MERGE queries.

        Relationships are grouped by type to use typed Cypher templates,
        ensuring Neo4j relationship labels match the domain model.

        Args:
            relationships: List of relationships to persist.

        Returns:
            Total number of relationships processed.
        """
        if not relationships:
            return 0

        grouped: dict[RelationType, list[dict[str, object]]] = {}
        for rel in relationships:
            props = rel.neo4j_properties()
            grouped.setdefault(rel.relation_type, []).append(props)

        total = 0
        async with self.driver.session(database=self._settings.database) as session:
            for rel_type, batch in grouped.items():
                cypher = _MERGE_RELATIONSHIP_TYPED.get(rel_type)
                if cypher is None:
                    logger.warning("No MERGE template for relation type: %s", rel_type)
                    continue
                try:
                    await session.execute_write(
                        self._run_batch_write, cypher, batch
                    )
                    total += len(batch)
                    logger.debug(
                        "Upserted %d %s relationships", len(batch), rel_type.value
                    )
                except Exception as exc:
                    raise Neo4jTransactionError(
                        f"Failed to upsert {rel_type.value} relationships: {exc}",
                        details={"rel_type": rel_type.value, "batch_size": len(batch)},
                    ) from exc

        return total

    # ──────────────────────────────────────────
    # Vector Search
    # ──────────────────────────────────────────

    async def vector_search(
        self,
        query_vector: list[float],
        top_k: int = 10,
    ) -> list[dict[str, object]]:
        """Execute a vector similarity search on Chunk embeddings.

        Args:
            query_vector: The query embedding vector.
            top_k: Number of results to return.

        Returns:
            List of dicts with 'node' properties and 'score'.
        """
        async with self.driver.session(database=self._settings.database) as session:
            try:
                result = await session.run(
                    _VECTOR_SEARCH,
                    query_vector=query_vector,
                    top_k=top_k,
                )
                records = [record.data() async for record in result]
                return records
            except Exception as exc:
                raise Neo4jQueryError(
                    f"Vector search failed: {exc}",
                    details={"top_k": top_k},
                ) from exc

    # ──────────────────────────────────────────
    # Graph Traversal
    # ──────────────────────────────────────────

    async def traverse_from_chunks(
        self,
        chunk_ids: list[str],
        depth: int = 2,
    ) -> list[dict[str, object]]:
        """Traverse graph outward from given chunks to discover context.

        Args:
            chunk_ids: Starting Chunk node IDs.
            depth: Maximum traversal hops (1-5).

        Returns:
            List of neighbor nodes and their connecting relationships.
        """
        if not chunk_ids:
            return []

        async with self.driver.session(database=self._settings.database) as session:
            try:
                result = await session.run(
                    _GRAPH_TRAVERSAL,
                    chunk_ids=chunk_ids,
                    depth=depth,
                )
                records = [record.data() async for record in result]
                return records
            except Exception as exc:
                raise Neo4jQueryError(
                    f"Graph traversal failed: {exc}",
                    details={"chunk_ids": chunk_ids, "depth": depth},
                ) from exc

    # ──────────────────────────────────────────
    # Health Check
    # ──────────────────────────────────────────

    async def check_connectivity(self) -> bool:
        """Verify the Neo4j connection is alive."""
        try:
            await self.driver.verify_connectivity()
            return True
        except Exception:
            return False

    # ──────────────────────────────────────────
    # Internal Helpers
    # ──────────────────────────────────────────

    @staticmethod
    async def _run_batch_write(
        tx: AsyncManagedTransaction,
        cypher: str,
        batch: list[dict[str, object]],
    ) -> None:
        """Execute a parameterized batch write within a managed transaction."""
        await tx.run(cypher, batch=batch)
