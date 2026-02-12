"""Text chunking utility.

Splits raw document text into overlapping chunks for embedding
and graph extraction. This is the first stage of the ingestion pipeline.
"""

import logging
from uuid import UUID

from app.config import ExtractionSettings
from app.domain.nodes import ChunkNode

logger = logging.getLogger(__name__)


class TextChunker:
    """Split raw text into overlapping ChunkNode instances.

    Uses a simple sliding-window approach with configurable size and overlap.
    For production, this can be swapped for a more sophisticated
    recursive or semantic chunker.

    Args:
        settings: Extraction configuration with chunk_size and chunk_overlap.
    """

    def __init__(self, settings: ExtractionSettings) -> None:
        self._chunk_size = settings.chunk_size
        self._chunk_overlap = settings.chunk_overlap

    def chunk_text(self, text: str, document_id: UUID) -> list[ChunkNode]:
        """Split text into overlapping chunks and return ChunkNode instances.

        Args:
            text: Raw document text.
            document_id: Parent document UUID for linking.

        Returns:
            Ordered list of ChunkNode instances.
        """
        if not text.strip():
            return []

        chunks: list[ChunkNode] = []
        start = 0
        index = 0

        while start < len(text):
            end = start + self._chunk_size
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append(
                    ChunkNode(
                        content=chunk_text,
                        chunk_index=index,
                        document_id=document_id,
                    )
                )
                index += 1

            # Advance window
            step = self._chunk_size - self._chunk_overlap
            if step <= 0:
                step = self._chunk_size  # Safety: prevent infinite loop
            start += step

        logger.debug(
            "Chunked text into %d chunks (size=%d, overlap=%d)",
            len(chunks),
            self._chunk_size,
            self._chunk_overlap,
        )
        return chunks
