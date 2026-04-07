"""Tests for evaluation API endpoints and RAGAS metrics."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.api.routes.evaluation import router
from app.main import app


@pytest.fixture
def client(mock_graph_store):
    """Create FastAPI test client with mocked graph store."""
    app.state.graph_store = mock_graph_store
    return TestClient(app)


@pytest.fixture
def mock_graph_store():
    """Mock GraphStore for evaluation operations."""
    store = AsyncMock()
    store._settings = MagicMock()
    store.get_evaluation_metrics = AsyncMock(return_value={
        "metrics": {
            "precision": {"value": 0.72, "trend": "up"},
            "recall": {"value": 0.81, "trend": "up"},
            "faithfulness": {"value": 0.88, "trend": "stable"},
            "relevance": {"value": 0.76, "trend": "up"},
        },
        "evaluated_queries": 100,
    })
    store.get_ablation_study = AsyncMock(return_value={
        "vector_only": {
            "precision": {"value": 0.65},
            "recall": {"value": 0.71},
            "faithfulness": {"value": 0.80},
            "relevance": {"value": 0.75},
        },
        "hybrid": {
            "precision": {"value": 0.72},
            "recall": {"value": 0.81},
            "faithfulness": {"value": 0.85},
            "relevance": {"value": 0.78},
        },
    })
    store.get_query_evaluations = AsyncMock(return_value=[])
    store.get_pipeline_configs = AsyncMock(return_value=[])
    store.create_pipeline_config = AsyncMock(return_value={})
    store.activate_pipeline_config = AsyncMock(return_value=True)
    store.get_pipeline_config = AsyncMock(return_value=None)
    store.get_prompt_templates = AsyncMock(return_value=[])
    store.create_prompt_template = AsyncMock(return_value={})
    return store


class TestEvaluationMetrics:
    def test_get_metrics_default_days(self, client, mock_graph_store):
        """Test getting evaluation metrics with default 7 days."""
        response = client.get("/api/v1/evaluation/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "precision" in data["metrics"]
        assert data["metrics"]["precision"]["value"] == 0.72
        assert data["evaluated_queries"] == 100

    def test_get_metrics_custom_days(self, client, mock_graph_store):
        """Test getting evaluation metrics with custom days parameter."""
        response = client.get("/api/v1/evaluation/metrics?days=30")

        assert response.status_code == 200
        # Verify the mock was called with correct parameter
        mock_graph_store.get_evaluation_metrics.assert_called_once_with(days=30)

    def test_get_metrics_structure(self, client, mock_graph_store):
        """Test that metrics response has correct structure."""
        response = client.get("/api/v1/evaluation/metrics")

        data = response.json()
        assert set(data["metrics"].keys()) == {"precision", "recall", "faithfulness", "relevance"}
        for metric in data["metrics"].values():
            assert "value" in metric
            assert isinstance(metric["value"], (int, float))


class TestAblationStudy:
    def test_get_ablation_study(self, client, mock_graph_store):
        """Test getting ablation study comparing vector-only vs hybrid."""
        response = client.get("/api/v1/evaluation/ablation-study")

        assert response.status_code == 200
        data = response.json()
        assert "vector_only" in data
        assert "hybrid" in data
        assert "improvement" in data

        # Check improvement calculations
        assert data["improvement"]["precision"] == pytest.approx(10.77)
        assert data["improvement"]["recall"] == pytest.approx(14.08, abs=0.02)

    def test_ablation_study_metrics_present(self, client, mock_graph_store):
        """Test that all expected metrics are present in ablation study."""
        response = client.get("/api/v1/evaluation/ablation-study")

        data = response.json()
        for mode in ["vector_only", "hybrid"]:
            assert "precision" in data[mode]
            assert "recall" in data[mode]
            assert "faithfulness" in data[mode]
            assert "relevance" in data[mode]


class TestQueryEvaluations:
    def test_get_query_evaluations_default(self, client, mock_graph_store):
        """Test getting individual query evaluations with defaults."""
        mock_graph_store.get_query_evaluations.return_value = [
            {
                "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "query_text": "What is Graph RAG?",
                "context_precision": 0.8,
                "context_recall": 0.9,
                "created_at": "2026-03-26T00:00:00Z",
            }
        ]

        response = client.get("/api/v1/evaluation/queries")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["context_precision"] == 0.8

    def test_get_query_evaluations_filtered(self, client, mock_graph_store):
        """Test getting query evaluations with filters."""
        response = client.get(
            "/api/v1/evaluation/queries?days=14&min_precision=0.7&limit=50"
        )

        assert response.status_code == 200
        mock_graph_store.get_query_evaluations.assert_called_once_with(
            days=14,
            min_precision=0.7,
            limit=50,
        )


class TestPipelineConfigs:
    def test_get_pipeline_configs(self, client, mock_graph_store):
        """Test retrieving all pipeline configurations."""
        mock_graph_store.get_pipeline_configs.return_value = [
            {
                "version": "v1.0.0",
                "is_active": True,
                "created_at": "2026-03-24T00:00:00Z",
                "created_by": "admin",
                "retrieval": {},
                "generation": {},
            },
            {
                "version": "v1.1.0",
                "is_active": False,
                "created_at": "2026-03-23T00:00:00Z",
                "created_by": "admin",
                "retrieval": {},
                "generation": {},
            },
        ]

        response = client.get("/api/v1/evaluation/pipeline/configs")

        assert response.status_code == 200
        data = response.json()
        assert len(data["configs"]) == 2
        assert data["configs"][0]["version"] == "v1.0.0"
        assert data["configs"][0]["is_active"] is True

    def test_create_pipeline_config(self, client, mock_graph_store):
        """Test creating a new pipeline configuration."""
        config_data = {
            "version": "v2.0.0",
            "retrieval": {"top_k": 10, "use_hybrid": True},
            "generation": {"model": "gpt-4", "temperature": 0.7},
            "change_summary": "Added hybrid retrieval",
        }

        mock_graph_store.create_pipeline_config.return_value = {
            "version": "v2.0.0",
            "retrieval": config_data["retrieval"],
            "generation": config_data["generation"],
            "created_by": "current_user",
            "created_at": "2026-03-26T00:00:00Z",
            "is_active": False,
        }

        response = client.post(
            "/api/v1/evaluation/pipeline/configs",
            json=config_data,
        )

        assert response.status_code == 201
        mock_graph_store.create_pipeline_config.assert_called_once()

    def test_activate_pipeline_config(self, client, mock_graph_store):
        """Test activating a pipeline configuration."""
        mock_graph_store.get_pipeline_config.return_value = {
            "version": "v2.0.0",
            "is_active": False,
        }

        response = client.post(
            "/api/v1/evaluation/pipeline/configs/v2.0.0/activate"
        )

        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "message": "Activated pipeline config v2.0.0",
        }
        mock_graph_store.activate_pipeline_config.assert_called_once_with("v2.0.0")


class TestPromptTemplates:
    def test_get_prompt_templates_all(self, client, mock_graph_store):
        """Test retrieving all prompt templates."""
        mock_graph_store.get_prompt_templates.return_value = [
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "retrieval-default",
                "template_type": "retrieval",
                "content": "Retrieve relevant context...",
                "variables": [],
                "version": "v1.0.0",
                "is_active": True,
                "created_at": "2026-03-24T00:00:00Z",
                "updated_at": "2026-03-24T00:00:00Z",
                "created_by": "admin",
            }
        ]

        response = client.get("/api/v1/evaluation/prompts")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_prompt_templates_filtered(self, client, mock_graph_store):
        """Test retrieving prompt templates filtered by type."""
        response = client.get("/api/v1/evaluation/prompts?template_type=retrieval")

        assert response.status_code == 200
        mock_graph_store.get_prompt_templates.assert_called_once_with(
            template_type="retrieval"
        )

    def test_create_prompt_template(self, client, mock_graph_store):
        """Test creating a new prompt template."""
        template_data = {
            "name": "generation-default",
            "template_type": "generation",
            "content": "Generate answer based on context...",
            "variables": ["context", "question"],
            "version": "v1.0.0",
        }

        mock_graph_store.create_prompt_template.return_value = {
            "id": "650e8400-e29b-41d4-a716-446655440001",
            "name": template_data["name"],
            "template_type": template_data["template_type"],
            "content": template_data["content"],
            "variables": template_data["variables"],
            "version": template_data["version"],
            "is_active": False,
            "created_at": "2026-03-26T00:00:00Z",
            "updated_at": "2026-03-26T00:00:00Z",
            "created_by": "current_user",
        }

        response = client.post(
            "/api/v1/evaluation/prompts",
            json=template_data,
        )

        assert response.status_code == 201
        mock_graph_store.create_prompt_template.assert_called_once()


class TestMetricsValidation:
    def test_metrics_values_in_range(self, client, mock_graph_store):
        """Test that metric values are within valid range [0, 1]."""
        response = client.get("/api/v1/evaluation/metrics")

        data = response.json()
        for metric_name, metric_data in data["metrics"].items():
            value = metric_data["value"]
            assert 0 <= value <= 1, f"{metric_name} value {value} out of range [0, 1]"

    def test_improvement_percentages(self, client, mock_graph_store):
        """Test that improvement percentages are calculated correctly."""
        response = client.get("/api/v1/evaluation/ablation-study")

        data = response.json()
        for metric, improvement in data["improvement"].items():
            assert isinstance(improvement, (int, float))
            assert improvement >= 0  # Improvements should be positive
