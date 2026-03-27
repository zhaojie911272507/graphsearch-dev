"""Tests for metadata management API endpoints (asset catalog, lineage, annotations, tags).

Covers:
- Asset catalog browsing and search
- Node detail views
- Data lineage tracing
- Annotations and votes
- Tags management
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_graph_store():
    """Mock GraphStore for metadata management operations."""
    store = AsyncMock()

    # Asset catalog
    store.get_metadata_assets = AsyncMock(return_value=[
        {
            "id": str(uuid4()),
            "node_type": "Entity",
            "name": "Neo4j",
            "entity_type": "TECHNOLOGY",
            "created_at": "2026-03-26T00:00:00Z",
            "relation_count": 5,
            "document_count": 3,
            "tags": ["database", "graph"],
            "confidence_avg": 0.85,
        }
    ])
    store.count_metadata_assets = AsyncMock(return_value=10)

    # Node detail
    store.get_node_by_id = AsyncMock(return_value={
        "id": str(uuid4()),
        "node_type": "Entity",
        "name": "Neo4j",
        "entity_type": "TECHNOLOGY",
        "description": "A graph database management system",
        "created_at": "2026-03-26T00:00:00Z",
        "updated_at": "2026-03-26T00:00:00Z",
        "source": "system",
        "tags": ["database", "graph"],
    })
    store.get_node_relations = AsyncMock(return_value={
        "relations": [
            {
                "relation_type": "RELATED_TO",
                "other_node_id": str(uuid4()),
                "other_node_name": "Graph Database",
                "other_node_type": "Concept",
                "weight": 0.9,
                "direction": "outgoing",
            }
        ]
    })

    # Lineage
    store.get_node_lineage = AsyncMock(return_value={
        "paths": [
            {
                "nodes": [
                    {"id": str(uuid4()), "type": "Document", "label": "Doc 1"},
                    {"id": str(uuid4()), "type": "Entity", "label": "Neo4j"},
                ],
                "confidence": 0.95,
            }
        ],
        "upstream_count": 1,
        "downstream_count": 0,
    })

    # Annotations
    store.get_node_annotations = AsyncMock(return_value=[
        {
            "id": str(uuid4()),
            "node_id": str(uuid4()),
            "user_id": "user-1",
            "annotation_type": "comment",
            "content": {"text": "Great technology!"},
            "status": "approved",
            "created_at": "2026-03-26T00:00:00Z",
            "updated_at": "2026-03-26T00:00:00Z",
            "votes": [],
        }
    ])
    store.create_annotation = AsyncMock(return_value={
        "id": str(uuid4()),
        "node_id": str(uuid4()),
        "user_id": "current_user",
        "annotation_type": "correction",
        "content": {"text": "Correction text"},
        "status": "pending",
        "created_at": "2026-03-26T00:00:00Z",
        "updated_at": "2026-03-26T00:00:00Z",
        "votes": [],
    })
    store.update_annotation = AsyncMock(return_value={
        "id": str(uuid4()),
        "node_id": str(uuid4()),
        "user_id": "current_user",
        "annotation_type": "correction",
        "content": {"text": "Updated correction"},
        "status": "approved",
        "created_at": "2026-03-26T00:00:00Z",
        "updated_at": "2026-03-26T01:00:00Z",
        "votes": [],
    })

    # Votes
    store.create_vote = AsyncMock(return_value={
        "id": str(uuid4()),
        "annotation_id": str(uuid4()),
        "user_id": "current_user",
        "vote_type": "upvote",
        "comment": "Good annotation",
        "created_at": "2026-03-26T00:00:00Z",
    })

    # Tags
    store.get_node_tags = AsyncMock(return_value=[
        {
            "id": str(uuid4()),
            "name": "database",
            "color": "#58a6ff",
            "created_by": "system",
            "created_at": "2026-03-26T00:00:00Z",
        },
        {
            "id": str(uuid4()),
            "name": "graph",
            "color": "#7ee787",
            "created_by": "user-1",
            "created_at": "2026-03-26T00:00:00Z",
        },
    ])

    return store


class TestAssetCatalog:
    """Test asset catalog browsing and search."""

    def test_list_assets_default(self, client, mock_graph_store):
        """Test listing assets with default parameters."""
        with patch("app.api.routes.metadata.GraphStore", return_value=mock_graph_store):
            response = client.get("/api/v1/metadata/assets")

            assert response.status_code == 200
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert "page" in data
            assert data["page"] == 1
            assert data["page_size"] == 20
            assert len(data["items"]) > 0

    def test_list_assets_with_filters(self, client, mock_graph_store):
        """Test listing assets with filters."""
        with patch("app.api.routes.metadata.GraphStore", return_value=mock_graph_store):
            response = client.get(
                "/api/v1/metadata/assets"
                "?type=Entity&entity_type=TECHNOLOGY&q=neo4j&tags=database,graph"
                "&page=1&page_size=10&sort_by=name&order=asc"
            )

            assert response.status_code == 200
            mock_graph_store.get_metadata_assets.assert_called_once_with(
                node_type="Entity",
                entity_type="TECHNOLOGY",
                search_query="neo4j",
                tags=["database", "graph"],
                sort_by="name",
                order="asc",
                limit=10,
                offset=0,
            )

    def test_list_assets_empty_result(self, client, mock_graph_store):
        """Test listing assets when no results match."""
        mock_graph_store.get_metadata_assets = AsyncMock(return_value=[])
        mock_graph_store.count_metadata_assets = AsyncMock(return_value=0)

        with patch("app.api.routes.metadata.GraphStore", return_value=mock_graph_store):
            response = client.get("/api/v1/metadata/assets?q=nonexistent")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert len(data["items"]) == 0


class TestNodeDetail:
    """Test node detail views."""

    def test_get_node_detail(self, client, mock_graph_store):
        """Test getting detailed information about a node."""
        node_id = str(uuid4())

        with patch("app.api.routes.metadata.GraphStore", return_value=mock_graph_store):
            response = client.get(f"/api/v1/metadata/{node_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["node_type"] == "Entity"
            assert data["name"] == "Neo4j"
            assert data["entity_type"] == "TECHNOLOGY"
            assert data["relation_count"] == 1
            assert len(data["outgoing_relations"]) == 1
            assert data["quality_score"] > 0

    def test_get_node_detail_not_found(self, client, mock_graph_store):
        """Test getting detail for non-existent node."""
        mock_graph_store.get_node_by_id = AsyncMock(return_value=None)

        with patch("app.api.routes.metadata.GraphStore", return_value=mock_graph_store):
            response = client.get(f"/api/v1/metadata/{uuid4()}")

            assert response.status_code == 404


class TestLineageTracking:
    """Test data lineage tracing."""

    def test_get_node_lineage_default(self, client, mock_graph_store):
        """Test getting node lineage with default parameters."""
        node_id = str(uuid4())

        with patch("app.api.routes.metadata.GraphStore", return_value=mock_graph_store):
            response = client.get(f"/api/v1/metadata/{node_id}/lineage")

            assert response.status_code == 200
            data = response.json()
            assert "lineage_paths" in data
            assert "upstream_count" in data
            assert "downstream_count" in data
            assert len(data["lineage_paths"]) > 0

    def test_get_node_lineage_upstream_only(self, client, mock_graph_store):
        """Test getting only upstream lineage."""
        node_id = str(uuid4())

        with patch("app.api.routes.metadata.GraphStore", return_value=mock_graph_store):
            response = client.get(f"/api/v1/metadata/{node_id}/lineage?direction=upstream")

            assert response.status_code == 200
            mock_graph_store.get_node_lineage.assert_called_once_with(
                node_id,
                direction="upstream",
                max_depth=3,
            )

    def test_get_node_lineage_downstream_only(self, client, mock_graph_store):
        """Test getting only downstream lineage."""
        node_id = str(uuid4())

        with patch("app.api.routes.metadata.GraphStore", return_value=mock_graph_store):
            response = client.get(f"/api/v1/metadata/{node_id}/lineage?direction=downstream")

            assert response.status_code == 200
            mock_graph_store.get_node_lineage.assert_called_once_with(
                node_id,
                direction="downstream",
                max_depth=3,
            )

    def test_get_node_lineage_custom_depth(self, client, mock_graph_store):
        """Test getting lineage with custom max depth."""
        node_id = str(uuid4())

        with patch("app.api.routes.metadata.GraphStore", return_value=mock_graph_store):
            response = client.get(f"/api/v1/metadata/{node_id}/lineage?max_depth=5")

            assert response.status_code == 200
            mock_graph_store.get_node_lineage.assert_called_once_with(
                node_id,
                direction="both",
                max_depth=5,
            )


class TestAnnotations:
    """Test annotation management."""

    def test_get_node_annotations(self, client, mock_graph_store):
        """Test getting annotations for a node."""
        node_id = str(uuid4())

        with patch("app.api.routes.metadata.GraphStore", return_value=mock_graph_store):
            response = client.get(f"/api/v1/metadata/{node_id}/annotations")

            assert response.status_code == 200
            data = response.json()
            assert len(data) > 0
            assert data[0]["annotation_type"] == "comment"
            assert data[0]["status"] == "approved"

    def test_get_node_annotations_filtered(self, client, mock_graph_store):
        """Test getting annotations with filters."""
        node_id = str(uuid4())

        with patch("app.api.routes.metadata.GraphStore", return_value=mock_graph_store):
            response = client.get(
                f"/api/v1/metadata/{node_id}/annotations"
                "?annotation_type=correction&status=pending"
            )

            assert response.status_code == 200
            mock_graph_store.get_node_annotations.assert_called_once_with(
                node_id,
                annotation_type="correction",
                status="pending",
            )

    def test_create_annotation_success(self, client, mock_graph_store):
        """Test creating a new annotation on a node."""
        node_id = str(uuid4())
        annotation_data = {
            "annotation_type": "correction",
            "content": {"text": "This should be updated"},
        }

        with patch("app.api.routes.metadata.GraphStore", return_value=mock_graph_store):
            response = client.post(
                f"/api/v1/metadata/{node_id}/annotations",
                json=annotation_data,
            )

            assert response.status_code == 201
            data = response.json()
            assert data["annotation_type"] == "correction"
            assert data["status"] == "pending"
            mock_graph_store.create_annotation.assert_called_once()

    def test_update_annotation_success(self, client, mock_graph_store):
        """Test updating an existing annotation."""
        annotation_id = str(uuid4())
        update_data = {
            "status": "approved",
            "content": {"text": "Updated content"},
        }

        with patch("app.api.routes.metadata.GraphStore", return_value=mock_graph_store):
            response = client.put(
                f"/api/v1/metadata/annotations/{annotation_id}",
                json=update_data,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "approved"
            mock_graph_store.update_annotation.assert_called_once()


class TestVotes:
    """Test voting on annotations."""

    def test_vote_annotation_success(self, client, mock_graph_store):
        """Test casting a vote on an annotation."""
        annotation_id = str(uuid4())
        vote_data = {
            "vote_type": "upvote",
            "comment": "Helpful annotation",
        }

        with patch("app.api.routes.metadata.GraphStore", return_value=mock_graph_store):
            response = client.post(
                f"/api/v1/metadata/annotations/{annotation_id}/votes",
                json=vote_data,
            )

            assert response.status_code == 201
            data = response.json()
            assert data["vote_type"] == "upvote"
            assert data["comment"] == "Helpful annotation"
            mock_graph_store.create_vote.assert_called_once()


class TestTags:
    """Test tag management."""

    def test_get_node_tags(self, client, mock_graph_store):
        """Test getting tags for a node."""
        node_id = str(uuid4())

        with patch("app.api.routes.metadata.GraphStore", return_value=mock_graph_store):
            response = client.get(f"/api/v1/metadata/{node_id}/tags")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "database"
            assert data[1]["name"] == "graph"
