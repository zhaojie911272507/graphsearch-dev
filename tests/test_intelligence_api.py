"""Tests for intelligence API endpoints (review queue, explorations, recommendations)."""

import pytest
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(mock_graph_store):
    """Create FastAPI test client with mocked graph store."""
    app.state.graph_store = mock_graph_store
    return TestClient(app)


@pytest.fixture
def mock_graph_store():
    """Mock GraphStore for intelligence operations."""
    store = AsyncMock()
    store.get_review_queue_items = AsyncMock(return_value=[])

    def create_exploration_path_side_effect(**kwargs):
        return {
            "id": str(uuid4()),
            "user_id": kwargs.get("user_id", "user-1"),
            "title": kwargs.get("title", "Test"),
            "description": kwargs.get("description", ""),
            "start_node_id": kwargs.get("start_node_id", str(uuid4())),
            "visited_nodes": kwargs.get("visited_nodes", []),
            "highlights": kwargs.get("highlights", []),
            "is_public": kwargs.get("is_public", True),
            "created_at": "2026-03-26T00:00:00Z",
            "updated_at": "2026-03-26T00:00:00Z",
        }

    store.create_exploration_path = AsyncMock(side_effect=create_exploration_path_side_effect)

    def get_exploration_paths_side_effect(**kwargs):
        return [
            {
                "id": str(uuid4()),
                "user_id": kwargs.get("user_id", "user-1"),
                "title": "Test Path",
                "description": "",
                "start_node_id": str(uuid4()),
                "visited_nodes": [],
                "highlights": [],
                "view_count": 10,
                "likes": 0,
                "is_public": True,
                "created_at": "2026-03-26T00:00:00Z",
                "updated_at": "2026-03-26T00:00:00Z",
            }
        ]

    store.get_exploration_paths = AsyncMock(side_effect=get_exploration_paths_side_effect)

    def get_recommendations_side_effect(**kwargs):
        return [
            {
                "id": str(uuid4()),
                "recommendation_type": "RELATED_ENTITY",
                "source_node_id": str(uuid4()),
                "source_node_name": "Source Entity",
                "target_node_id": str(uuid4()),
                "target_node_name": "Related Entity",
                "target_node_type": "Entity",
                "confidence": 0.85,
                "reason": "Co-occurrence",
                "metadata": {},
            }
        ]

    store.get_recommendations = AsyncMock(side_effect=get_recommendations_side_effect)
    return store


class TestReviewQueue:
    def test_get_review_queue(self, client, mock_graph_store):
        """Test retrieving items from review queue."""
        mock_graph_store.get_review_queue_items.return_value = [
            {
                "id": str(uuid4()),
                "node_id": str(uuid4()),
                "node_type": "Entity",
                "node_name": "Test",
                "reason": "Low confidence",
                "auto_confidence": 0.5,
                "source_document": "",
                "original_text": "",
                "status": "pending",
                "vote_count": 0,
                "approve_count": 0,
                "reject_count": 0,
                "modify_count": 0,
                "created_at": "2026-03-26T00:00:00Z",
                "priority": 0.8,
            }
        ]

        response = client.get("/api/v1/intelligence/review-queue?status_filter=pending")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "pending"

    def test_get_review_queue_empty(self, client, mock_graph_store):
        """Test retrieving empty review queue."""
        mock_graph_store.get_review_queue_items.return_value = []

        response = client.get("/api/v1/intelligence/review-queue")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


class TestExplorations:
    def test_create_exploration_success(self, client, mock_graph_store):
        """Test creating an exploration path."""
        response = client.post(
            "/api/v1/intelligence/explorations",
            json={
                "title": "Test Exploration",
                "description": "A test exploration path",
                "start_node_id": str(uuid4()),
                "visited_nodes": [str(uuid4()), str(uuid4())],
                "highlights": [],
                "is_public": True,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == "Test Exploration"
        mock_graph_store.create_exploration_path.assert_called_once()

    def test_get_explorations(self, client, mock_graph_store):
        """Test retrieving exploration paths."""
        mock_graph_store.get_explorations.return_value = [
            {
                "id": str(uuid4()),
                "user_id": "user-1",
                "title": "Test Path",
                "description": "",
                "start_node_id": str(uuid4()),
                "visited_nodes": [],
                "highlights": [],
                "view_count": 10,
                "likes": 0,
                "is_public": True,
                "created_at": "2026-03-26T00:00:00Z",
                "updated_at": "2026-03-26T00:00:00Z",
            }
        ]

        response = client.get("/api/v1/intelligence/explorations?user_id=user-1")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Path"


class TestRecommendations:
    def test_get_recommendations(self, client, mock_graph_store):
        """Test getting recommendations for a node."""
        mock_graph_store.get_recommendations.return_value = [
            {
                "id": str(uuid4()),
                "recommendation_type": "RELATED_ENTITY",
                "target_node_id": str(uuid4()),
                "target_node_name": "Related Entity",
                "confidence": 0.85,
                "reason": "Co-occurrence",
            }
        ]

        response = client.get("/api/v1/intelligence/recommendations?node_id={}".format(uuid4()))

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["confidence"] == 0.85
