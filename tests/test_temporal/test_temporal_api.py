"""Tests for temporal API routes."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch


# Mock temporal services before importing the router
@pytest.fixture
def mock_temporal_services():
    """Create mock temporal services."""
    mock_store = AsyncMock()
    mock_version_manager = AsyncMock()
    mock_summary_generator = AsyncMock()
    mock_batch_merger = AsyncMock()

    return {
        "temporal_store": mock_store,
        "version_manager": mock_version_manager,
        "summary_generator": mock_summary_generator,
        "batch_merger": mock_batch_merger,
    }


@pytest.fixture
def setup_temporal_routes(mock_temporal_services):
    """Set up temporal routes with mock services."""
    from app.api.routes.temporal import set_temporal_services

    set_temporal_services(
        temporal_store=mock_temporal_services["temporal_store"],
        version_manager=mock_temporal_services["version_manager"],
        summary_generator=mock_temporal_services["summary_generator"],
        batch_merger=mock_temporal_services["batch_merger"],
    )

    return mock_temporal_services


class TestTemporalQuery:
    """Tests for temporal query endpoint."""

    @pytest.mark.asyncio
    async def test_entity_history_query(self, setup_temporal_routes, mock_temporal_services):
        """Test entity history query."""
        from app.api.routes.temporal import temporal_query
        from app.api.schemas.temporal import TemporalQueryRequest
        from app.domain.temporal import EntityVersion

        # Setup mock
        mock_version_manager = mock_temporal_services["version_manager"]
        entity_id = uuid4()
        now = datetime.now(timezone.utc)

        mock_version_manager.get_entity_history = AsyncMock(
            return_value=[
                EntityVersion(
                    id=uuid4(),
                    entity_id=entity_id,
                    version=1,
                    timestamp=now,
                    properties={"name": "Test", "description": "Test entity"},
                    change_summary="Created",
                    source_document_ids=[],
                )
            ]
        )

        request = TemporalQueryRequest(
            entity_id=entity_id,
            query_type="entity_history",
        )

        response = await temporal_query(request)

        assert response.query_type == "entity_history"
        assert len(response.results) == 1
        assert response.metadata["count"] == 1

    @pytest.mark.asyncio
    async def test_entity_at_time_query(self, setup_temporal_routes, mock_temporal_services):
        """Test entity at time query."""
        from app.api.routes.temporal import temporal_query
        from app.api.schemas.temporal import TemporalQueryRequest
        from app.domain.temporal import EntityVersion

        mock_version_manager = mock_temporal_services["version_manager"]
        entity_id = uuid4()
        now = datetime.now(timezone.utc)

        mock_version_manager.get_entity_at_time = AsyncMock(
            return_value=EntityVersion(
                id=uuid4(),
                entity_id=entity_id,
                version=1,
                timestamp=now,
                properties={"name": "Test", "description": "Test entity"},
                change_summary="Created",
                source_document_ids=[],
            )
        )

        request = TemporalQueryRequest(
            entity_id=entity_id,
            query_type="entity_at_time",
            timestamp=now,
        )

        response = await temporal_query(request)

        assert response.query_type == "entity_at_time"
        assert len(response.results) == 1

    @pytest.mark.asyncio
    async def test_relationship_history_query(self, setup_temporal_routes, mock_temporal_services):
        """Test relationship history query."""
        from app.api.routes.temporal import temporal_query
        from app.api.schemas.temporal import TemporalQueryRequest
        from app.domain.temporal import RelationshipSnapshot

        mock_version_manager = mock_temporal_services["version_manager"]
        source_id = uuid4()
        target_id = uuid4()
        now = datetime.now(timezone.utc)

        mock_version_manager.get_relationship_history = AsyncMock(
            return_value=[
                RelationshipSnapshot(
                    id=uuid4(),
                    source_id=source_id,
                    target_id=target_id,
                    relation_type="KNOWS",
                    valid_from=now,
                    valid_to=None,
                    properties={},
                    weight=0.8,
                    is_current=True,
                )
            ]
        )

        request = TemporalQueryRequest(
            source_id=source_id,
            target_id=target_id,
            query_type="relationship_history",
        )

        response = await temporal_query(request)

        assert response.query_type == "relationship_history"
        assert len(response.results) == 1
        assert response.results[0]["relation_type"] == "KNOWS"

    @pytest.mark.asyncio
    async def test_invalid_query_type(self, setup_temporal_routes, mock_temporal_services):
        """Test invalid query type."""
        from app.api.routes.temporal import temporal_query
        from app.api.schemas.temporal import TemporalQueryRequest
        from fastapi import HTTPException

        request = TemporalQueryRequest(
            query_type="invalid_type",
        )

        with pytest.raises(HTTPException) as exc_info:
            await temporal_query(request)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_entity_id(self, setup_temporal_routes, mock_temporal_services):
        """Test missing entity_id for entity_history query."""
        from app.api.routes.temporal import temporal_query
        from app.api.schemas.temporal import TemporalQueryRequest
        from fastapi import HTTPException

        request = TemporalQueryRequest(
            query_type="entity_history",
        )

        with pytest.raises(HTTPException) as exc_info:
            await temporal_query(request)

        assert exc_info.value.status_code == 400


class TestSummaryGeneration:
    """Tests for summary generation endpoint."""

    @pytest.mark.asyncio
    async def test_entity_summary(self, setup_temporal_routes, mock_temporal_services):
        """Test entity summary generation."""
        from app.api.routes.temporal import generate_summary
        from app.api.schemas.temporal import SummaryRequest
        from app.domain.temporal import EntitySummary

        mock_summary_generator = mock_temporal_services["summary_generator"]
        entity_id = uuid4()
        now = datetime.now(timezone.utc)

        mock_summary_generator.generate_entity_summary = AsyncMock(
            return_value=EntitySummary(
                entity_id=entity_id,
                entity_name="Test Entity",
                entity_type="Person",
                current_description="A test entity",
                version_count=5,
                first_seen=now,
                last_updated=now,
                change_history=[],
                importance_score=0.8,
            )
        )

        request = SummaryRequest(
            level="entity",
            entity_id=entity_id,
            entity_name="Test Entity",
            entity_type="Person",
        )

        response = await generate_summary(request)

        assert response.level == "entity"
        assert response.content["entity_name"] == "Test Entity"
        assert response.content["version_count"] == 5

    @pytest.mark.asyncio
    async def test_relationship_summary(self, setup_temporal_routes, mock_temporal_services):
        """Test relationship summary generation."""
        from app.api.routes.temporal import generate_summary
        from app.api.schemas.temporal import SummaryRequest
        from app.domain.temporal import RelationshipSummary

        mock_summary_generator = mock_temporal_services["summary_generator"]
        source_id = uuid4()
        target_id = uuid4()

        mock_summary_generator.generate_relationship_summary = AsyncMock(
            return_value=RelationshipSummary(
                source_id=source_id,
                target_id=target_id,
                relation_type="KNOWS",
                duration_days=30,
                snapshot_count=3,
                strength_trend="rising",
                key_events=[],
            )
        )

        request = SummaryRequest(
            level="relationship",
            source_id=source_id,
            target_id=target_id,
            relation_type="KNOWS",
        )

        response = await generate_summary(request)

        assert response.level == "relationship"
        assert response.content["relation_type"] == "KNOWS"
        assert response.content["duration_days"] == 30

    @pytest.mark.asyncio
    async def test_global_summary(self, setup_temporal_routes, mock_temporal_services):
        """Test global summary generation."""
        from app.api.routes.temporal import generate_summary
        from app.api.schemas.temporal import SummaryRequest
        from app.domain.temporal import GlobalSummary

        mock_summary_generator = mock_temporal_services["summary_generator"]
        now = datetime.now(timezone.utc)

        mock_summary_generator.generate_global_summary = AsyncMock(
            return_value=GlobalSummary(
                generated_at=now,
                total_entities=100,
                total_versions=500,
                total_snapshots=200,
                top_entities=[],
                entity_trend={"added": 10, "modified": 5},
                relationship_density=0.5,
            )
        )

        request = SummaryRequest(level="global")

        response = await generate_summary(request)

        assert response.level == "global"
        assert response.content["total_entities"] == 100
        assert response.content["total_versions"] == 500

    @pytest.mark.asyncio
    async def test_invalid_summary_level(self, setup_temporal_routes, mock_temporal_services):
        """Test invalid summary level."""
        from app.api.routes.temporal import generate_summary
        from app.api.schemas.temporal import SummaryRequest
        from fastapi import HTTPException

        request = SummaryRequest(level="invalid")

        with pytest.raises(HTTPException) as exc_info:
            await generate_summary(request)

        assert exc_info.value.status_code == 400


class TestStatusEndpoint:
    """Tests for status endpoint."""

    @pytest.mark.asyncio
    async def test_get_status(self, setup_temporal_routes, mock_temporal_services):
        """Test getting temporal service status."""
        from app.api.routes.temporal import get_status
        from app.api.schemas.temporal import TemporalStatusResponse

        mock_batch_merger = mock_temporal_services["batch_merger"]
        now = datetime.now(timezone.utc)

        mock_batch_merger.get_status = MagicMock(
            return_value={
                "running": True,
                "pending_count": 10,
                "last_merge_time": now.isoformat(),
                "interval_minutes": 5,
            }
        )

        response = await get_status()

        assert isinstance(response, TemporalStatusResponse)
        assert response.running is True
        assert response.pending_count == 10
        assert response.interval_minutes == 5


class TestMergeEndpoint:
    """Tests for merge endpoint."""

    @pytest.mark.asyncio
    async def test_trigger_merge(self, setup_temporal_routes, mock_temporal_services):
        """Test triggering manual merge."""
        from app.api.routes.temporal import trigger_merge
        from app.api.schemas.temporal import MergeResponse

        mock_batch_merger = mock_temporal_services["batch_merger"]
        now = datetime.now(timezone.utc)

        mock_batch_merger.trigger_manual_merge = AsyncMock(
            return_value={
                "running": True,
                "pending_count": 0,
                "last_merge_time": now.isoformat(),
                "interval_minutes": 5,
            }
        )

        response = await trigger_merge()

        assert isinstance(response, MergeResponse)
        assert response.success is True
        assert response.status.running is True

    @pytest.mark.asyncio
    async def test_merge_when_not_initialized(self):
        """Test merge when temporal services not initialized."""
        from app.api.routes.temporal import router, trigger_merge, set_temporal_services

        # Reset temporal services
        set_temporal_services(None, None, None, None)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await trigger_merge()

        assert exc_info.value.status_code == 503

        # Restore mock services for other tests
        mock_batch_merger = AsyncMock()
        mock_batch_merger.get_status = MagicMock(
            return_value={
                "running": True,
                "pending_count": 0,
                "last_merge_time": None,
                "interval_minutes": 5,
            }
        )
        mock_batch_merger.trigger_manual_merge = AsyncMock(
            return_value={
                "running": True,
                "pending_count": 0,
                "last_merge_time": None,
                "interval_minutes": 5,
            }
        )
        set_temporal_services(None, None, None, mock_batch_merger)