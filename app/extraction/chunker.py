"""Text chunking utility.

Splits raw document text into semantically meaningful chunks for embedding
and graph extraction. This is the first stage of the ingestion pipeline.

Inspired by MiroFish's approach to semantic-aware chunking.
"""

import logging
import re
from uuid import UUID

from app.config import ExtractionSettings
from app.domain.nodes import ChunkNode

logger = logging.getLogger(__name__)


class TextChunker:
    """Split raw text into semantically meaningful chunks.

    Uses a multi-strategy approach inspired by MiroFish:
    1. First, split by natural semantic boundaries (paragraphs, sections)
    2. Then, merge or split based on token count targets
    3. Preserve context by including minimal overlap at boundaries
    4. Handle special content: code blocks, lists, tables

    Args:
        settings: Extraction configuration with chunk_size and chunk_overlap.
    """

    def __init__(self, settings: ExtractionSettings) -> None:
        self._chunk_size = settings.chunk_size
        self._chunk_overlap = settings.chunk_overlap
        # Estimate tokens per char (rough approximation for English)
        self._chars_per_token = 4

    def chunk_text(self, text: str, document_id: UUID) -> list[ChunkNode]:
        """Split text into semantically meaningful chunks.

        Strategy (MiroFish-inspired):
        1. Split by paragraphs (double newlines) as the primary semantic unit
        2. Group paragraphs into chunks that approach target size
        3. Add overlap by including the last sentence of previous chunk
        4. Handle edge cases: code blocks, lists, tables

        Args:
            text: Raw document text.
            document_id: Parent document UUID for linking.

        Returns:
            Ordered list of ChunkNode instances with semantic coherence.
        """
        if not text.strip():
            return []

        # Step 1: Split into semantic units (paragraphs)
        paragraphs = self._split_into_paragraphs(text)

        # Step 2: Group paragraphs into chunks
        chunks = self._group_into_chunks(paragraphs, document_id)

        logger.debug(
            "Chunked text into %d semantic chunks (target_size=%d, overlap=%d)",
            len(chunks),
            self._chunk_size,
            self._chunk_overlap,
        )
        return chunks

    def _split_into_paragraphs(self, text: str) -> list[str]:
        """Split text into semantic units (paragraphs).

        Handles:
        - Standard paragraphs (double newlines)
        - Section headers (single lines followed by content)
        - List items (preserved as groups)
        - Code blocks (preserved as single units)

        Args:
            text: Raw document text.

        Returns:
            List of paragraph strings.
        """
        # First, normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Split by double newline to get paragraph blocks
        raw_paragraphs = re.split(r'\n\n+', text)

        paragraphs = []
        for para in raw_paragraphs:
            para = para.strip()
            if not para:
                continue

            # Check if this is a code block (preserve as single unit)
            if para.startswith('```') or para.startswith('    ') or para.startswith('\t'):
                paragraphs.append(para)
                continue

            # Check if this is a list (group list items together)
            if re.match(r'^[\s]*[-*+]\s', para) or re.match(r'^[\s]*\d+\.', para):
                paragraphs.append(para)
                continue

            # Check if this is a header (short line, possibly with # or ===)
            if len(para) < 200 and ('#' in para[:10] or para.startswith('===') or para.startswith('---')):
                paragraphs.append(para)
                continue

            # Standard paragraph - check if it contains multiple sentences
            # If very long, we might need to sub-split
            if len(para) > self._chunk_size * 2:
                sub_splits = self._split_by_sentences(para)
                paragraphs.extend(sub_splits)
            else:
                paragraphs.append(para)

        return paragraphs

    def _split_by_sentences(self, text: str) -> list[str]:
        """Split a long paragraph into sentence groups.

        Used when a single paragraph exceeds target chunk size.

        Args:
            text: A long paragraph to split.

        Returns:
            List of sentence group strings.
        """
        # Simple sentence splitting (handles common cases)
        sentences = re.split(r'(?<=[.!?])\s+', text)

        if len(sentences) <= 1:
            return [text]

        # Group sentences into chunks of roughly equal size
        groups = []
        current_group = []
        current_length = 0
        target_group_size = self._chunk_size // 2

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            current_length += len(sentence)
            current_group.append(sentence)

            if current_length >= target_group_size:
                groups.append(' '.join(current_group))
                current_group = []
                current_length = 0

        if current_group:
            groups.append(' '.join(current_group))

        return groups if groups else [text]

    def _group_into_chunks(self, paragraphs: list[str], document_id: UUID) -> list[ChunkNode]:
        """Group paragraphs into chunks respecting target size.

        Uses a greedy algorithm:
        1. Accumulate paragraphs until approaching target size
        2. When exceeded, create chunk and start new one
        3. Add overlap by including last sentence from previous chunk
        4. Track semantic metadata (section titles, word count, etc.)

        Args:
            paragraphs: List of paragraph strings.
            document_id: Parent document UUID.

        Returns:
            List of ChunkNode instances with semantic metadata.
        """
        if not paragraphs:
            return []

        chunks: list[ChunkNode] = []
        current_chunk_parts: list[str] = []
        current_length = 0
        chunk_index = 0
        previous_chunk_text: str | None = None
        previous_section_title: str = ""
        current_section_title: str = ""

        for para in paragraphs:
            para_length = len(para)

            # Detect section headers
            if self._is_section_header(para):
                current_section_title = self._extract_section_title(para)
                previous_section_title = current_section_title

            # If adding this paragraph would exceed target
            if current_length + para_length > self._chunk_size and current_chunk_parts:
                # Create chunk from accumulated parts
                chunk_text = '\n\n'.join(current_chunk_parts)

                # Add overlap from previous chunk
                overlap_text = ""
                if previous_chunk_text and self._chunk_overlap > 0:
                    overlap_text = self._get_overlap_text(previous_chunk_text, self._chunk_overlap)
                    if overlap_text:
                        chunk_text = overlap_text + '\n\n' + chunk_text

                # Calculate metadata
                word_count = len(chunk_text.split())
                sentence_count = len(re.findall(r'[.!?]+', chunk_text))

                chunks.append(
                    ChunkNode(
                        content=chunk_text,
                        chunk_index=chunk_index,
                        document_id=document_id,
                        section_title=previous_section_title,
                        paragraph_type=self._detect_paragraph_type(chunk_text),
                        word_count=word_count,
                        sentence_count=sentence_count,
                        semantic_boundary_start=True,
                        semantic_boundary_end=True,
                        previous_chunk_overlap=overlap_text,
                    )
                )

                # Save overlap for next chunk
                previous_chunk_text = chunk_text
                chunk_index += 1

                # Start new chunk with current paragraph
                current_chunk_parts = [para]
                current_length = para_length
            else:
                # Add paragraph to current chunk
                current_chunk_parts.append(para)
                current_length += para_length

        # Don't forget the last chunk
        if current_chunk_parts:
            chunk_text = '\n\n'.join(current_chunk_parts)

            # Add overlap from previous chunk
            overlap_text = ""
            if previous_chunk_text and self._chunk_overlap > 0:
                overlap_text = self._get_overlap_text(previous_chunk_text, self._chunk_overlap)
                if overlap_text:
                    chunk_text = overlap_text + '\n\n' + chunk_text

            # Calculate metadata
            word_count = len(chunk_text.split())
            sentence_count = len(re.findall(r'[.!?]+', chunk_text))

            chunks.append(
                ChunkNode(
                    content=chunk_text,
                    chunk_index=chunk_index,
                    document_id=document_id,
                    section_title=previous_section_title,
                    paragraph_type=self._detect_paragraph_type(chunk_text),
                    word_count=word_count,
                    sentence_count=sentence_count,
                    semantic_boundary_start=True,
                    semantic_boundary_end=True,
                    previous_chunk_overlap=overlap_text,
                )
            )

        return chunks

    def _get_overlap_text(self, text: str, max_overlap_chars: int) -> str:
        """Extract overlap text from the end of previous chunk.

        Tries to find a natural break point (sentence boundary)
        within the overlap size.

        Args:
            text: Previous chunk text.
            max_overlap_chars: Maximum overlap size in characters.

        Returns:
            Overlap text string (may be empty if no natural break found).
        """
        if len(text) <= max_overlap_chars:
            return text

        # Try to find a sentence boundary
        overlap_region = text[-max_overlap_chars:]

        # Look for sentence endings
        for match in re.finditer(r'[.!?]\s+', overlap_region):
            # Return from start of overlap region to after the sentence ending
            return overlap_region[:match.end()]

        # If no sentence boundary, just return the overlap region
        return overlap_region

    def _is_section_header(self, text: str) -> bool:
        """Detect if text is a section header.

        Args:
            text: Paragraph text to check.

        Returns:
            True if this appears to be a section header.
        """
        # Check for markdown headers
        if text.startswith('#'):
            return True

        # Check for underline style headers (=== or ---)
        if text.startswith('===') or text.startswith('---'):
            return True

        # Short line that might be a title (under 100 chars, no ending punctuation)
        if len(text) < 100 and not text.endswith(('.', '!', '?')):
            return True

        return False

    def _extract_section_title(self, text: str) -> str:
        """Extract clean section title from header text.

        Args:
            text: Header paragraph text.

        Returns:
            Clean section title string.
        """
        # Remove markdown # symbols
        title = re.sub(r'^#+\s*', '', text)

        # Remove underline markers
        title = re.sub(r'^[=\-]+\s*$', '', title)

        return title.strip()

    def _detect_paragraph_type(self, text: str) -> str:
        """Detect the type of content in a paragraph.

        Args:
            text: Paragraph text to analyze.

        Returns:
            Type string: paragraph/list/code/table/header/other.
        """
        text_stripped = text.strip()

        # Code block detection
        if text_stripped.startswith('```'):
            return 'code'

        # Indented code detection
        if text_stripped.startswith('    ') or text_stripped.startswith('\t'):
            return 'code'

        # List detection
        if re.match(r'^[\s]*[-*+]\s', text_stripped):
            return 'list'

        if re.match(r'^[\s]*\d+\.', text_stripped):
            return 'numbered_list'

        # Header detection
        if text_stripped.startswith('#'):
            return 'header'

        # Table detection (simple heuristic)
        if '|' in text_stripped and text_stripped.count('|') >= 2:
            return 'table'

        # Quote detection
        if text_stripped.startswith('>'):
            return 'quote'

        return 'paragraph'
