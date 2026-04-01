"""Tests for pipeline configuration."""

import pytest
from datetime import datetime
from app.api.schemas.evaluation import (
    PipelineConfigSchema,
    PipelineConfigCreateSchema,
    PipelineConfigListResponseSchema,
)


class TestPipelineConfigSchema:
    """Tests for pipeline configuration schemas."""

    def test_pipeline_config_schema(self):
        """Test pipeline config schema."""
        from app.api.schemas.evaluation import PipelineConfigSchema

        config = PipelineConfigSchema(
            version="v1.0.0",
            retrieval={
                "ingestion": {"enabled": True, "params": {"max_file_size": 10485760}},
                "chunking": {"enabled": True, "params": {"chunk_size": 500}},
                "extraction": {"enabled": True, "params": {"model": "gpt-4o"}},
                "graph_storage": {"enabled": True, "params": {"batch_size": 100}},
                "vector_index": {"enabled": True, "params": {"dimension": 1024}},
                "query": {"enabled": True, "params": {"top_k": 5}},
            },
            generation={},
            created_at=datetime.now(),
            created_by="admin",
            is_active=True,
        )

        assert config.version == "v1.0.0"
        assert config.is_active is True
        assert config.retrieval["ingestion"]["enabled"] is True

    def test_pipeline_config_create_schema(self):
        """Test pipeline config create schema."""
        from app.api.schemas.evaluation import PipelineConfigCreateSchema

        config = PipelineConfigCreateSchema(
            version="v1.0.0",
            retrieval={},
            generation={},
            change_summary="Initial configuration",
        )

        assert config.version == "v1.0.0"
        assert config.change_summary == "Initial configuration"

    def test_pipeline_config_version_pattern(self):
        """Test version pattern validation."""
        from app.api.schemas.evaluation import PipelineConfigCreateSchema
        from pydantic import ValidationError

        # Valid version
        config = PipelineConfigCreateSchema(
            version="v1.0.0",
            retrieval={},
            generation={},
        )
        assert config.version == "v1.0.0"

        # Invalid version (should fail)
        with pytest.raises(ValidationError):
            PipelineConfigCreateSchema(
                version="invalid",
                retrieval={},
                generation={},
            )


class TestPipelineConfigAPI:
    """Tests for pipeline configuration API."""

    def test_pipeline_endpoint_exists(self):
        """Test pipeline endpoints exist in routes."""
        from app.api.routes import evaluation

        # Check that routes have pipeline configs
        routes = [r.path for r in evaluation.router.routes]
        assert "/pipeline/configs" in routes or any("pipeline" in r for r in routes)

    def test_get_pipeline_configs_response(self):
        """Test pipeline configs response schema."""
        from app.api.schemas.evaluation import PipelineConfigListResponseSchema

        response = PipelineConfigListResponseSchema(
            configs=[
                PipelineConfigSchema(
                    version="v1.0.0",
                    retrieval={},
                    generation={},
                    created_at=datetime.now(),
                    created_by="admin",
                    is_active=True,
                ),
                PipelineConfigSchema(
                    version="v0.9.0",
                    retrieval={},
                    generation={},
                    created_at=datetime.now(),
                    created_by="admin",
                    is_active=False,
                ),
            ],
            active_version="v1.0.0",
        )

        assert len(response.configs) == 2
        assert response.active_version == "v1.0.0"