"""Tests for the GraphExtractor (LLM-based entity extraction)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.config import ExtractionSettings, OpenAISettings
from app.domain.nodes import ChunkNode
from app.extraction.extractor import GraphExtractor


@pytest.fixture
def extractor() -> GraphExtractor:
    """Create extractor with mocked LLM."""
    openai_settings = OpenAISettings(api_key="sk-test")
    extraction_settings = ExtractionSettings(max_concurrency=2, max_retries=1)
    return GraphExtractor(
        openai_settings=openai_settings,
        extraction_settings=extraction_settings,
    )


@pytest.fixture
def sample_chunk() -> ChunkNode:
    """Create a sample chunk for extraction tests."""
    return ChunkNode(
        content="OpenAI is an AI research company based in San Francisco.",
        chunk_index=0,
        document_id=uuid4(),
    )


class TestGraphExtractor:
    """Tests for GraphExtractor parsing logic."""

    def test_parse_valid_llm_response(self, extractor: GraphExtractor) -> None:
        raw_json = json.dumps(
            {
                "entities": [
                    {
                        "name": "OpenAI",
                        "entity_type": "ORG",
                        "description": "AI research company",
                    },
                    {
                        "name": "San Francisco",
                        "entity_type": "LOCATION",
                        "description": "City in California",
                    },
                ],
                "concepts": [
                    {
                        "name": "Artificial Intelligence",
                        "definition": "Machine intelligence",
                    }
                ],
                "relationships": [
                    {
                        "source_name": "OpenAI",
                        "target_name": "San Francisco",
                        "relation_type": "RELATED_TO",
                        "weight": 0.8,
                    }
                ],
            }
        )

        result = extractor._parse_llm_response(raw_json, uuid4())
        assert len(result.entities) == 2
        assert len(result.concepts) == 1
        assert len(result.relationships) == 1
        assert result.entities[0].name == "OpenAI"
        assert result.relationships[0].weight == 0.8

    def test_parse_empty_response(self, extractor: GraphExtractor) -> None:
        raw_json = json.dumps({"entities": [], "concepts": [], "relationships": []})
        result = extractor._parse_llm_response(raw_json, uuid4())
        assert len(result.entities) == 0
        assert len(result.concepts) == 0
        assert len(result.relationships) == 0

    def test_parse_invalid_json_raises(self, extractor: GraphExtractor) -> None:
        from app.exceptions import LLMResponseParsingError

        with pytest.raises(LLMResponseParsingError):
            extractor._parse_llm_response("not valid json {{{", uuid4())

    def test_relationship_skipped_if_endpoint_missing(
        self, extractor: GraphExtractor
    ) -> None:
        raw_json = json.dumps(
            {
                "entities": [
                    {"name": "Alice", "entity_type": "PERSON", "description": ""},
                ],
                "concepts": [],
                "relationships": [
                    {
                        "source_name": "Alice",
                        "target_name": "NonExistent",
                        "relation_type": "RELATED_TO",
                        "weight": 0.5,
                    }
                ],
            }
        )

        result = extractor._parse_llm_response(raw_json, uuid4())
        assert len(result.entities) == 1
        assert len(result.relationships) == 0  # Skipped

    def test_unknown_entity_type_defaults_to_other(
        self, extractor: GraphExtractor
    ) -> None:
        raw_json = json.dumps(
            {
                "entities": [
                    {"name": "X", "entity_type": "UNKNOWN_TYPE", "description": ""},
                ],
                "concepts": [],
                "relationships": [],
            }
        )
        from app.domain.enums import EntityType

        result = extractor._parse_llm_response(raw_json, uuid4())
        assert result.entities[0].entity_type == EntityType.OTHER
