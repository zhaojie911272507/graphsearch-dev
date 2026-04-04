"""Batch merger for temporal knowledge graph."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from app.config import TemporalSettings

logger = logging.getLogger(__name__)


class PendingItem:
    """Pending item for batch processing."""

    def __init__(
        self,
        item_type: str,
        data: dict[str, Any],
        document_id: str
    ) -> None:
        self.item_type = item_type  # "entity_version" or "relationship_snapshot"
        self.data = data
        self.document_id = document_id
        self.created_at = datetime.utcnow()


class BatchMerger:
    """Handles batch merging of temporal data with scheduled execution."""

    def __init__(
        self,
        temporal_settings: TemporalSettings,
        version_manager: "VersionManager | None" = None,
        summary_generator: "SummaryGenerator | None" = None
    ) -> None:
        self._settings = temporal_settings
        self._version_manager = version_manager
        self._summary_generator = summary_generator
        self._queue: asyncio.Queue[PendingItem] = asyncio.Queue()
        self._task: asyncio.Task | None = None
        self._running = False
        self._last_merge_time: datetime | None = None

    def set_version_manager(self, version_manager: "VersionManager") -> None:
        self._version_manager = version_manager

    def set_summary_generator(self, summary_generator: "SummaryGenerator") -> None:
        self._summary_generator = summary_generator

    async def add_to_queue(
        self,
        item_type: str,
        data: dict[str, Any],
        document_id: str
    ) -> None:
        """Add item to pending queue."""
        item = PendingItem(item_type, data, document_id)
        await self._queue.put(item)
        logger.debug(
            "Added %s to pending queue (document: %s)",
            item_type,
            document_id
        )

    async def start(self) -> None:
        """Start the batch merger scheduler."""
        if self._running:
            logger.warning("BatchMerger already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info(
            "BatchMerger started with interval %d minutes",
            self._settings.batch_interval_minutes
        )

    async def stop(self) -> None:
        """Stop the batch merger scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("BatchMerger stopped")

    async def _run_scheduler(self) -> None:
        """Main scheduler loop."""
        interval = self._settings.batch_interval_minutes * 60  # Convert to seconds

        while self._running:
            try:
                await asyncio.sleep(interval)
                await self._merge_task()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in batch merger: %s", e)
                # Continue on error
                await asyncio.sleep(60)  # Wait before retry

    async def _merge_task(self) -> None:
        """Execute batch merge."""
        if not self._version_manager:
            logger.warning("Version manager not set, skipping merge")
            return

        # Collect pending items
        items: list[PendingItem] = []
        max_items = 100  # Process in batches

        while not self._queue.empty() and len(items) < max_items:
            try:
                item = self._queue.get_nowait()
                items.append(item)
            except asyncio.QueueEmpty:
                break

        if not items:
            logger.debug("No pending items to merge")
            return

        logger.info("Processing %d pending items", len(items))

        # Process entity versions
        entity_items = [i for i in items if i.item_type == "entity_version"]
        # Process relationship snapshots
        relationship_items = [i for i in items if i.item_type == "relationship_snapshot"]

        # Here we would call version_manager to persist
        # For now just log the counts
        logger.info(
            "Merging: %d entity versions, %d relationship snapshots",
            len(entity_items),
            len(relationship_items)
        )

        # Trigger summary generation if enabled
        if self._settings.summary_enabled and self._summary_generator:
            try:
                # Generate global summary after merge
                asyncio.create_task(
                    self._summary_generator.generate_global_summary()
                )
            except Exception as e:
                logger.warning("Failed to generate summary: %s", e)

        self._last_merge_time = datetime.utcnow()
        logger.info("Batch merge completed at %s", self._last_merge_time)

    def get_status(self) -> dict[str, Any]:
        """Get merger status."""
        return {
            "running": self._running,
            "pending_count": self._queue.qsize(),
            "last_merge_time": self._last_merge_time.isoformat() if self._last_merge_time else None,
            "interval_minutes": self._settings.batch_interval_minutes
        }

    async def trigger_manual_merge(self) -> dict[str, Any]:
        """Manually trigger a merge."""
        await self._merge_task()
        return self.get_status()