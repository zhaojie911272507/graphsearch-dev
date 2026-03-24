"""Tests for GraphStore index management."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import Neo4jSettings
from app.persistence.graph_store import GraphStore


@pytest.fixture
def mock_session():
    """Mock Neo4j async session."""
    session = AsyncMock()
    session.run = AsyncMock()
    return session


@pytest.fixture
def graph_store():
    """Create GraphStore instance with mocked settings."""
    settings = MagicMock()
    settings.uri = "bolt://localhost:7687"
    settings.username = "neo4j"
    settings.password = "test"
    settings.database = "neo4j"

    store = GraphStore(settings)
    return store


class TestIndexCreation:
    @pytest.mark.asyncio
    async def test_create_indexes_success(self, graph_store, mock_driver, mock_session):
        """Test that create_indexes creates all required indexes."""
        with patch.object(GraphStore, "driver", mock_driver):
            result = await graph_store.create_indexes()

            # Verify session.run was called for each index query
            assert mock_session.run.call_count == 6  # 6 index creation queries

            # Verify return structure
            assert "annotation_indexes" in result
            assert "vote_indexes" in result
            assert "exploration_indexes" in result
            assert "evaluation_indexes" in result
            assert "pipeline_indexes" in result
            assert "prompt_indexes" in result
            assert "total" in result
            assert result["total"] == 24  # 6 queries * 4 indexes each

    @pytest.mark.asyncio
    async def test_create_indexes_failure(self, graph_store, mock_driver, mock_session):
        """Test that create_indexes handles errors gracefully."""
        from app.exceptions import Neo4jQueryError

        mock_session.run.side_effect = Exception("Index creation failed")

        with patch.object(GraphStore, "driver", mock_driver):
            with pytest.raises(Neo4jQueryError) as exc_info:
                await graph_store.create_indexes()

            assert "Failed to create additional indexes" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_index_stats_success(self, graph_store, mock_driver, mock_session):
        """Test that get_index_stats retrieves index information."""
        mock_record = MagicMock()
        mock_record.__getitem__.side_effect = lambda key: {
            "name": "test_index",
            "labelsOrTypes": ["TestLabel"],
            "properties": ["test_prop"],
            "state": "ONLINE",
            "type": "BTREE",
        }[key]

        mock_session.run.return_value = AsyncMock(
            __aiter__=lambda self: iter([mock_record]),
            __anext__=lambda self: mock_record,
        )

        with patch.object(GraphStore, "driver", mock_driver):
            result = await graph_store.get_index_stats()

            # Verify session.run was called with correct query
            mock_session.run.assert_called_once()
            call_args = mock_session.run.call_args
            assert "CALL db.indexes()" in str(call_args)

            # Verify return structure
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["name"] == "test_index"
            assert result[0]["state"] == "ONLINE"

    @pytest.mark.asyncio
    async def test_get_index_stats_failure(self, graph_store, mock_driver, mock_session):
        """Test that get_index_stats handles errors gracefully."""
        from app.exceptions import Neo4jQueryError

        mock_session.run.side_effect = Exception("Failed to get index stats")

        with patch.object(GraphStore, "driver", mock_driver):
            with pytest.raises(Neo4jQueryError) as exc_info:
                await graph_store.get_index_stats()

            assert "Failed to get index statistics" in str(exc_info.value)


class TestEnsureIndexes:
    @pytest.mark.asyncio
    async def test_ensure_indexes_with_dimension(self, graph_store, mock_driver, mock_session):
        """Test that ensure_indexes creates vector index with custom dimension."""
        with patch.object(GraphStore, "driver", mock_driver):
            await graph_store.ensure_indexes(dimension=768)

            # Verify vector index was created with correct dimension
            call_args = mock_session.run.call_args_list[-1]
            assert call_args[0][0]  # Query string
            assert call_args[1]["dimension"] == 768

    @pytest.mark.asyncio
    async def test_ensure_indexes_default_dimension(self, graph_store, mock_driver, mock_session):
        """Test that ensure_indexes uses default dimension."""
        with patch.object(GraphStore, "driver", mock_driver):
            await graph_store.ensure_indexes()

            # Verify default dimension was used
            call_args = mock_session.run.call_args_list[-1]
            assert call_args[1]["dimension"] == 1024


class TestIndexIdempotency:
    @pytest.mark.asyncio
    async def test_indexes_are_idempotent(self, graph_store, mock_driver, mock_session):
        """Test that index creation is idempotent (uses IF NOT EXISTS)."""
        with patch.object(GraphStore, "driver", mock_driver):
            await graph_store.create_indexes()

            # Verify all queries use IF NOT EXISTS
            all_queries = [call[0][0] for call in mock_session.run.call_args_list]
            for query in all_queries:
                assert "IF NOT EXISTS" in query or "IF NOT EXISTS" in query.upper()
