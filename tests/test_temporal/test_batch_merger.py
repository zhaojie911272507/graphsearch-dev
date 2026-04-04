"""Tests for batch merger."""

import pytest
import asyncio
from datetime import datetime
from uuid import uuid4

from app.config import TemporalSettings
from app.services.temporal_knowledge.batch_merger import BatchMerger, PendingItem


@pytest.fixture
def temporal_settings():
    return TemporalSettings(batch_interval_minutes=1, summary_enabled=False)


@pytest.fixture
def batch_merger(temporal_settings):
    return BatchMerger(temporal_settings)


def test_batch_merger_initialization(batch_merger):
    assert batch_merger is not None
    assert batch_merger._running is False


def test_pending_item_creation():
    item = PendingItem(
        item_type="entity_version",
        data={"entity_id": str(uuid4())},
        document_id="doc-123"
    )

    assert item.item_type == "entity_version"
    assert item.data["entity_id"]
    assert item.created_at is not None


@pytest.mark.asyncio
async def test_add_to_queue(batch_merger):
    await batch_merger.add_to_queue(
        item_type="entity_version",
        data={"test": "data"},
        document_id="doc-123"
    )

    assert batch_merger._queue.qsize() == 1


@pytest.mark.asyncio
async def test_start_stop(batch_merger):
    await batch_merger.start()
    assert batch_merger._running is True

    await batch_merger.stop()
    assert batch_merger._running is False


def test_get_status(batch_merger):
    status = batch_merger.get_status()

    assert "running" in status
    assert "pending_count" in status
    assert "last_merge_time" in status
    assert status["interval_minutes"] == 1