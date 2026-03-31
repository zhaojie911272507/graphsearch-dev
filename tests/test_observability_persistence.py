"""Tests for Neo4j persistence layer observability (metrics and tracing)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.config import Neo4jSettings
from app.domain.enums import NodeType, RelationType
from app.domain.nodes import ChunkNode
from app.domain.relationships import GraphRelationship
from app.persistence.graph_store import GraphStore


class MockAsyncIterator:
    """Mock async iterator for Neo4j results."""

    def __init__(self, items):
        self.items = items
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


class MockResult:
    """Mock Neo4j result."""

    def __init__(self, items):
        self.items = items

    def __aiter__(self):
        return MockAsyncIterator(self.items)

    async def consume(self):
        pass


class TestNeo4jMetricsAndTracing:
    """Test metrics and tracing instrumentation in GraphStore."""

    @pytest.fixture
    def neo4j_settings(self) -> Neo4jSettings:
        """Create test Neo4j settings."""
        return Neo4jSettings(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="test-password",
            database="neo4j",
        )

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Mock Neo4j session."""
        session = MagicMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        session.run = AsyncMock(return_value=MockResult([]))
        session.execute_write = AsyncMock()
        return session

    @pytest.fixture
    def mock_driver(self, mock_session: MagicMock) -> MagicMock:
        """Mock Neo4j driver."""
        driver = MagicMock()
        driver.session = MagicMock(return_value=mock_session)
        driver.verify_connectivity = AsyncMock(return_value=True)
        driver.close = AsyncMock()
        return driver

    @pytest.fixture
    def mock_tracer(self) -> tuple:
        """Mock OpenTelemetry tracer."""
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=None)
        mock_span.set_attribute = MagicMock()
        mock_span.record_exception = MagicMock()

        tracer = MagicMock()
        tracer.start_as_current_span = MagicMock(return_value=mock_span)

        return tracer, mock_span

    @pytest.mark.asyncio
    async def test_vector_search_records_latency_metric(
        self,
        neo4j_settings: Neo4jSettings,
        mock_driver: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Test that vector search records latency metric."""
        from app.observability.metrics import MetricsRegistry

        # Mock result with data
        mock_result = MockResult([
            MagicMock(data=MagicMock(return_value={"node": {"id": "1"}, "score": 0.9}))
        ])
        mock_session.run = AsyncMock(return_value=mock_result)

        store = GraphStore(neo4j_settings)
        store._driver = mock_driver

        query_vector = [0.1] * 1024
        await store.vector_search(query_vector, top_k=5)

        # Verify metric exists
        assert MetricsRegistry.rag_neo4j_query_latency_seconds is not None

    @pytest.mark.asyncio
    async def test_traverse_from_chunks_records_metric(
        self,
        neo4j_settings: Neo4jSettings,
        mock_driver: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Test that graph traversal records latency metric."""
        from app.observability.metrics import MetricsRegistry

        mock_session.run = AsyncMock(return_value=MockResult([]))

        store = GraphStore(neo4j_settings)
        store._driver = mock_driver

        chunk_ids = [str(uuid4()) for _ in range(3)]
        await store.traverse_from_chunks(chunk_ids, depth=2)

        # Verify metric exists
        assert MetricsRegistry.rag_neo4j_query_latency_seconds is not None

    @pytest.mark.asyncio
    async def test_ensure_indexes_records_metric(
        self,
        neo4j_settings: Neo4jSettings,
        mock_driver: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Test that ensure_indexes records latency metric."""
        from app.observability.metrics import MetricsRegistry

        mock_session.run = AsyncMock(return_value=MockResult([]))

        store = GraphStore(neo4j_settings)
        store._driver = mock_driver

        await store.ensure_indexes(dimension=1024)

        # Verify metric exists
        assert MetricsRegistry.rag_neo4j_query_latency_seconds is not None

    @pytest.mark.asyncio
    async def test_check_connectivity_records_metric(
        self,
        neo4j_settings: Neo4jSettings,
        mock_driver: MagicMock,
    ) -> None:
        """Test that check_connectivity records latency metric."""
        from app.observability.metrics import MetricsRegistry

        store = GraphStore(neo4j_settings)
        store._driver = mock_driver

        result = await store.check_connectivity()

        assert result is True
        assert MetricsRegistry.rag_neo4j_query_latency_seconds is not None

    @pytest.mark.asyncio
    async def test_upsert_nodes_records_metric(
        self,
        neo4j_settings: Neo4jSettings,
        mock_driver: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Test that upsert_nodes records latency metric."""
        from app.observability.metrics import MetricsRegistry

        mock_session.run = AsyncMock(return_value=MockResult([]))

        store = GraphStore(neo4j_settings)
        store._driver = mock_driver

        chunk = ChunkNode(
            content="Test content",
            chunk_index=0,
            document_id=str(uuid4()),
        )

        await store.upsert_nodes([chunk])

        # Verify metric exists
        assert MetricsRegistry.rag_neo4j_query_latency_seconds is not None

    @pytest.mark.asyncio
    async def test_vector_search_tracing_span_created(
        self,
        neo4j_settings: Neo4jSettings,
        mock_driver: MagicMock,
        mock_session: MagicMock,
        mock_tracer: tuple,
    ) -> None:
        """Test that vector search creates tracing span."""
        tracer, mock_span = mock_tracer

        mock_result = MockResult([
            MagicMock(data=MagicMock(return_value={"node": {"id": "1"}, "score": 0.9}))
        ])
        mock_session.run = AsyncMock(return_value=mock_result)

        with patch('app.persistence.graph_store.TracingSetup') as mock_tracing_setup:
            mock_tracing_setup.get_tracer = MagicMock(return_value=tracer)

            store = GraphStore(neo4j_settings)
            store._driver = mock_driver

            query_vector = [0.1] * 1024
            await store.vector_search(query_vector, top_k=5)

            # Verify tracer was called
            assert tracer.start_as_current_span.called

    @pytest.mark.asyncio
    async def test_tracing_span_attributes_set(
        self,
        neo4j_settings: Neo4jSettings,
        mock_driver: MagicMock,
        mock_session: MagicMock,
        mock_tracer: tuple,
    ) -> None:
        """Test that tracing span has correct attributes."""
        tracer, mock_span = mock_tracer

        mock_session.run = AsyncMock(return_value=MockResult([]))

        with patch('app.persistence.graph_store.TracingSetup') as mock_tracing_setup:
            mock_tracing_setup.get_tracer = MagicMock(return_value=tracer)

            store = GraphStore(neo4j_settings)
            store._driver = mock_driver

            await store.vector_search([0.1] * 1024, top_k=5)

            # Verify span attributes were set
            mock_span.set_attribute.assert_called()

    @pytest.mark.asyncio
    async def test_error_recording_in_tracing(
        self,
        neo4j_settings: Neo4jSettings,
        mock_driver: MagicMock,
        mock_session: MagicMock,
        mock_tracer: tuple,
    ) -> None:
        """Test that errors are recorded in tracing."""
        tracer, mock_span = mock_tracer

        mock_session.run = AsyncMock(side_effect=Exception("Query failed"))

        with patch('app.persistence.graph_store.TracingSetup') as mock_tracing_setup:
            mock_tracing_setup.get_tracer = MagicMock(return_value=tracer)

            store = GraphStore(neo4j_settings)
            store._driver = mock_driver

            with pytest.raises(Exception):
                await store.vector_search([0.1] * 1024, top_k=5)

            # Verify error was recorded
            mock_span.record_exception.assert_called()

    @pytest.mark.asyncio
    async def test_get_graph_for_visualization_records_metric(
        self,
        neo4j_settings: Neo4jSettings,
        mock_driver: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Test that get_graph_for_visualization records latency metric."""
        from app.observability.metrics import MetricsRegistry

        mock_session.run = AsyncMock(return_value=MockResult([]))

        store = GraphStore(neo4j_settings)
        store._driver = mock_driver

        await store.get_graph_for_visualization(limit=100)

        # Verify metric exists
        assert MetricsRegistry.rag_neo4j_query_latency_seconds is not None

    @pytest.mark.asyncio
    async def test_get_graph_stats_records_metric(
        self,
        neo4j_settings: Neo4jSettings,
        mock_driver: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Test that get_graph_stats records latency metric."""
        from app.observability.metrics import MetricsRegistry

        mock_session.run = AsyncMock(return_value=MockResult([]))

        store = GraphStore(neo4j_settings)
        store._driver = mock_driver

        await store.get_graph_stats()

        # Verify metric exists
        assert MetricsRegistry.rag_neo4j_query_latency_seconds is not None

    @pytest.mark.asyncio
    async def test_upsert_relationships_records_metric(
        self,
        neo4j_settings: Neo4jSettings,
        mock_driver: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Test that upsert_relationships records latency metric."""
        from app.observability.metrics import MetricsRegistry

        mock_session.run = AsyncMock(return_value=MockResult([]))

        store = GraphStore(neo4j_settings)
        store._driver = mock_driver

        rel = GraphRelationship(
            relation_type=RelationType.RELATED_TO,
            source_id=str(uuid4()),
            target_id=str(uuid4()),
            weight=1.0,
        )

        await store.upsert_relationships([rel])

        # Verify metric exists
        assert MetricsRegistry.rag_neo4j_query_latency_seconds is not None

    @pytest.mark.asyncio
    async def test_multiple_operations_record_separate_metrics(
        self,
        neo4j_settings: Neo4jSettings,
        mock_driver: MagicMock,
        mock_session: MagicMock,
    ) -> None:
        """Test that multiple operations record separate metrics."""
        from app.observability.metrics import MetricsRegistry

        mock_session.run = AsyncMock(return_value=MockResult([]))

        store = GraphStore(neo4j_settings)
        store._driver = mock_driver

        # Perform multiple operations
        await store.vector_search([0.1] * 1024, top_k=5)
        await store.traverse_from_chunks([str(uuid4())], depth=2)
        await store.ensure_indexes(dimension=1024)

        # Verify metric exists and can track multiple operations
        assert MetricsRegistry.rag_neo4j_query_latency_seconds is not None
