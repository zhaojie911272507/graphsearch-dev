"""Tests for intelligence API endpoints (annotations, votes, explorations)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.api.routes.intelligence import router
from app.main import app


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_graph_store():
    """Mock GraphStore for intelligence operations."""
    store = AsyncMock()
    store.create_annotation = AsyncMock(return_value={"id": "anno-1", "status": "pending"})
    store.get_annotations = AsyncMock(return_value=[])
    store.vote_annotation = AsyncMock(return_value={"success": True})
    store.get_review_queue = AsyncMock(return_value=[])
    store.create_exploration_path = AsyncMock(return_value={"id": "expl-1"})
    store.get_explorations = AsyncMock(return_value=[])
    store.get_recommendations = AsyncMock(return_value=[])
    store.get_user_contributions = AsyncMock(return_value={})
    return store


class TestAnnotations:
    def test_create_annotation_success(self, client, mock_graph_store):
        """Test creating an annotation."""
        with patch("app.api.routes.intelligence.GraphStore", return_value=mock_graph_store):
            response = client.post(
                "/api/v1/intelligence/annotations",
                json={
                    "node_id": "node-1",
                    "annotation_type": "comment",
                    "content": {"text": "Great insight!"},
                },
            )

            assert response.status_code == 200
            assert response.json()["status"] == "pending"
            mock_graph_store.create_annotation.assert_called_once()

    def test_create_annotation_missing_fields(self, client, mock_graph_store):
        """Test creating annotation with missing required fields."""
        with patch("app.api.routes.intelligence.GraphStore", return_value=mock_graph_store):
            response = client.post(
                "/api/v1/intelligence/annotations",
                json={"node_id": "node-1"},  # Missing annotation_type and content
            )

            # Should fail validation
            assert response.status_code in [400, 422]

    def test_get_annotations(self, client, mock_graph_store):
        """Test retrieving annotations for a node."""
        mock_graph_store.get_annotations.return_value = [
            {"id": "anno-1", "annotation_type": "comment", "content": {"text": "Test"}},
        ]

        with patch("app.api.routes.intelligence.GraphStore", return_value=mock_graph_store):
            response = client.get("/api/v1/intelligence/annotations?node_id=node-1")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["annotation_type"] == "comment"


class TestVotes:
    def test_vote_annotation_success(self, client, mock_graph_store):
        """Test voting on an annotation."""
        with patch("app.api.routes.intelligence.GraphStore", return_value=mock_graph_store):
            response = client.post(
                "/api/v1/intelligence/votes",
                json={
                    "annotation_id": "anno-1",
                    "vote_type": "upvote",
                    "user_id": "user-1",
                },
            )

            assert response.status_code == 200
            assert response.json()["success"] is True
            mock_graph_store.vote_annotation.assert_called_once()

    def test_vote_annotation_invalid_type(self, client, mock_graph_store):
        """Test voting with invalid vote type."""
        with patch("app.api.routes.intelligence.GraphStore", return_value=mock_graph_store):
            response = client.post(
                "/api/v1/intelligence/votes",
                json={
                    "annotation_id": "anno-1",
                    "vote_type": "invalid_type",  # Should be upvote/downvote
                    "user_id": "user-1",
                },
            )

            # Should fail validation
            assert response.status_code in [400, 422]


class TestReviewQueue:
    def test_get_review_queue(self, client, mock_graph_store):
        """Test retrieving items from review queue."""
        mock_graph_store.get_review_queue.return_value = [
            {
                "id": "item-1",
                "annotation_type": "correction",
                "status": "pending",
                "priority": 0.8,
            }
        ]

        with patch("app.api.routes.intelligence.GraphStore", return_value=mock_graph_store):
            response = client.get("/api/v1/intelligence/review-queue?status_filter=pending")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["status"] == "pending"

    def test_vote_review(self, client, mock_graph_store):
        """Test voting on a review queue item."""
        with patch("app.api.routes.intelligence.GraphStore", return_value=mock_graph_store):
            response = client.post(
                "/api/v1/intelligence/review-queue/item-1/vote",
                json={
                    "vote_type": "approve",
                    "comment": "Looks good!",
                },
            )

            assert response.status_code == 200


class TestExplorations:
    def test_create_exploration_success(self, client, mock_graph_store):
        """Test creating an exploration path."""
        with patch("app.api.routes.intelligence.GraphStore", return_value=mock_graph_store):
            response = client.post(
                "/api/v1/intelligence/explorations",
                json={
                    "title": "Test Exploration",
                    "description": "A test exploration path",
                    "start_node_id": "node-1",
                    "visited_nodes": ["node-1", "node-2", "node-3"],
                },
            )

            assert response.status_code == 200
            assert "id" in response.json()
            mock_graph_store.create_exploration_path.assert_called_once()

    def test_get_explorations(self, client, mock_graph_store):
        """Test retrieving exploration paths."""
        mock_graph_store.get_explorations.return_value = [
            {
                "id": "expl-1",
                "title": "Test Path",
                "user_id": "user-1",
                "view_count": 10,
            }
        ]

        with patch("app.api.routes.intelligence.GraphStore", return_value=mock_graph_store):
            response = client.get("/api/v1/intelligence/explorations?user_id=user-1")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["view_count"] == 10


class TestRecommendations:
    def test_get_recommendations(self, client, mock_graph_store):
        """Test getting recommendations for a node."""
        mock_graph_store.get_recommendations.return_value = [
            {
                "id": "rec-1",
                "recommendation_type": "RELATED_ENTITY",
                "target_node_name": "Related Entity",
                "confidence": 0.85,
            }
        ]

        with patch("app.api.routes.intelligence.GraphStore", return_value=mock_graph_store):
            response = client.get("/api/v1/intelligence/recommendations?node_id=node-1")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["confidence"] == 0.85


class TestUserContributions:
    def test_get_user_contributions(self, client, mock_graph_store):
        """Test retrieving user contribution statistics."""
        mock_graph_store.get_user_contributions.return_value = {
            "user_id": "user-1",
            "annotations_count": 5,
            "votes_count": 10,
            "explorations_count": 2,
            "reputation_score": 17.0,
        }

        with patch("app.api.routes.intelligence.GraphStore", return_value=mock_graph_store):
            response = client.get("/api/v1/intelligence/user-contributions/user-1")

            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "user-1"
            assert data["annotations_count"] == 5
            assert data["reputation_score"] == 17.0
