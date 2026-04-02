"""Tests for summary generator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4

from app.config import OpenAISettings, TemporalSettings
from app.services.temporal_knowledge.summary_generator import SummaryGenerator


@pytest.fixture
def openai_settings():
    return OpenAISettings(api_key="test-key")


@pytest.fixture
def temporal_settings():
    return TemporalSettings(summary_enabled=False)


@pytest.fixture
def summary_generator(openai_settings, temporal_settings):
    with patch("langchain_openai.ChatOpenAI"):
        generator = SummaryGenerator(openai_settings, temporal_settings)
        return generator


def test_summary_generator_initialization(summary_generator):
    assert summary_generator is not None


def test_set_version_manager(summary_generator):
    mock_manager = MagicMock()
    summary_generator.set_version_manager(mock_manager)
    assert summary_generator._version_manager == mock_manager


def test_set_temporal_store(summary_generator):
    mock_store = MagicMock()
    summary_generator.set_temporal_store(mock_store)
    assert summary_generator._temporal_store == mock_store


@pytest.mark.asyncio
async def test_generate_entity_summary_without_manager(summary_generator):
    with pytest.raises(RuntimeError, match="Version manager not set"):
        await summary_generator.generate_entity_summary(uuid4(), "Test", "PERSON")


@pytest.mark.asyncio
async def test_generate_entity_summary_empty_history(summary_generator):
    mock_manager = MagicMock()
    mock_manager.get_entity_history = AsyncMock(return_value=[])
    summary_generator.set_version_manager(mock_manager)

    result = await summary_generator.generate_entity_summary(
        uuid4(), "Test", "PERSON"
    )

    assert result.entity_name == "Test"
    assert result.entity_type == "PERSON"
    assert result.version_count == 0
    assert result.importance_score == 0.0


@pytest.mark.asyncio
async def test_generate_entity_summary_with_history(summary_generator):
    entity_id = uuid4()
    mock_manager = MagicMock()
    mock_manager.get_entity_history = AsyncMock(
        return_value=[
            MagicMock(
                entity_id=entity_id,
                version=1,
                timestamp=datetime(2024, 1, 1),
                properties={"description": "Initial description"},
                change_summary="Created",
            ),
            MagicMock(
                entity_id=entity_id,
                version=2,
                timestamp=datetime(2024, 1, 2),
                properties={"description": "Updated description"},
                change_summary="Updated",
            ),
        ]
    )
    summary_generator.set_version_manager(mock_manager)

    result = await summary_generator.generate_entity_summary(
        entity_id, "Test Entity", "PERSON"
    )

    assert result.entity_name == "Test Entity"
    assert result.version_count == 2
    assert result.importance_score == 0.2  # min(1.0, 2/10)


@pytest.mark.asyncio
async def test_generate_relationship_summary_without_manager(summary_generator):
    with pytest.raises(RuntimeError, match="Version manager not set"):
        await summary_generator.generate_relationship_summary(
            uuid4(), uuid4(), "Source", "Target", "KNOWS"
        )


@pytest.mark.asyncio
async def test_generate_relationship_summary_empty(summary_generator):
    mock_manager = MagicMock()
    mock_manager.get_relationship_history = AsyncMock(return_value=[])
    summary_generator.set_version_manager(mock_manager)

    result = await summary_generator.generate_relationship_summary(
        uuid4(), uuid4(), "Source", "Target", "KNOWS"
    )

    assert result.relation_type == "KNOWS"
    assert result.snapshot_count == 0
    assert result.strength_trend == "stable"


@pytest.mark.asyncio
async def test_generate_relationship_summary_with_snapshots(summary_generator):
    source_id = uuid4()
    target_id = uuid4()
    mock_manager = MagicMock()
    mock_manager.get_relationship_history = AsyncMock(
        return_value=[
            MagicMock(
                valid_from=datetime(2024, 1, 2),
                weight=0.8,
                properties={"type": "colleague"},
            ),
            MagicMock(
                valid_from=datetime(2024, 1, 1),
                weight=0.5,
                properties={"type": "acquaintance"},
            ),
        ]
    )
    summary_generator.set_version_manager(mock_manager)

    result = await summary_generator.generate_relationship_summary(
        source_id, target_id, "Source", "Target", "KNOWS"
    )

    assert result.snapshot_count == 2
    assert result.duration_days == 1
    assert result.strength_trend == "rising"  # 0.8 > 0.5 + 0.2


@pytest.mark.asyncio
async def test_generate_global_summary_without_store(summary_generator):
    with pytest.raises(RuntimeError, match="Temporal store not set"):
        await summary_generator.generate_global_summary()


@pytest.mark.asyncio
async def test_generate_global_summary(summary_generator):
    mock_store = MagicMock()
    mock_store.get_global_stats = AsyncMock(
        return_value={
            "total_entities": 100,
            "total_versions": 250,
            "total_snapshots": 150,
        }
    )
    summary_generator.set_temporal_store(mock_store)

    result = await summary_generator.generate_global_summary()

    assert result.total_entities == 100
    assert result.total_versions == 250
    assert result.total_snapshots == 150


def test_summary_generator_requires_api_key():
    settings_no_key = OpenAISettings(api_key="")
    temporal_settings = TemporalSettings()

    with pytest.raises(ValueError, match="OpenAI API key required"):
        SummaryGenerator(settings_no_key, temporal_settings)