"""Text chunking utility with improved token-aware strategies.

Splits raw document text into semantically meaningful chunks for embedding
and graph extraction. Supports multiple chunking strategies.

Features:
- Token-based chunking using tiktoken for accurate token counting
- Intelligent sentence boundary detection
- Multiple strategies: fixed, recursive
- Configurable overlap between chunks
"""

import logging
import re
from abc import ABC, abstractmethod
from uuid import UUID

import tiktoken

from app.config import ExtractionSettings
from app.domain.nodes import ChunkNode

logger = logging.getLogger(__name__)


class TokenCounter:
    """Accurate token counting using tiktoken."""

    _encoding_cache: dict[str, tiktoken.Encoding] = {}

    def __init__(self, model: str = "cl100k_base") -> None:
        self._model = model

    def _get_encoding(self) -> tiktoken.Encoding:
        """Get or create encoding instance (cached)."""
        if self._model not in self._encoding_cache:
            self._encoding_cache[self._model] = tiktoken.get_encoding(self._model)
        return self._encoding_cache[self._model]

    def count(self, text: str) -> int:
        """Count tokens in text accurately."""
        encoding = self._get_encoding()
        return len(encoding.encode(text))


class SentenceSplitter:
    """Intelligent sentence boundary detection.

    Handles edge cases:
    - Abbreviations: Mr., Dr., etc.
    - Numbers: 1.5, 2024.12.31
    - Ellipsis: ...
    - Common patterns
    """

    # Patterns that should NOT be treated as sentence endings
    _abbreviation_patterns = [
        r'\b(Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|e\.g|i\.d)\.$',
        r'\b[A-Z]\.\s*[A-Z]\.',  # E. G. Smith
    ]

    # Decimal numbers and version numbers
    _number_pattern = r'\d+\.\d+|\d+\.\d+\.\d+'

    def __init__(self) -> None:
        self._abbreviation_regex = re.compile('|'.join(self._abbreviation_patterns), re.IGNORECASE)

    def split(self, text: str) -> list[str]:
        """Split text into sentences intelligently."""
        if not text.strip():
            return []

        # First, protect special patterns by replacing them with placeholders
        protected = self._protect_patterns(text)

        # Split on sentence-ending punctuation followed by whitespace
        sentences = re.split(r'(?<=[.!?])\s+', protected)

        # Restore protected patterns and filter
        result = []
        for sent in sentences:
            sent = self._restore_patterns(sent).strip()
            if sent and len(sent) > 1:
                result.append(sent)

        return result

    def _protect_patterns(self, text: str) -> str:
        """Replace patterns that shouldn't be split with placeholders."""
        # Protect abbreviations
        for i, pattern in enumerate(self._abbreviation_patterns):
            text = re.sub(pattern, f'__ABBR_{i}__', text, flags=re.IGNORECASE)

        # Protect decimal numbers
        text = re.sub(self._number_pattern, lambda m: m.group(0).replace('.', '__DOT__'), text)

        return text

    def _restore_patterns(self, text: str) -> str:
        """Restore protected patterns."""
        # Restore abbreviations
        for i in range(10):
            text = text.replace(f'__ABBR_{i}__', '')

        # Restore decimal numbers
        text = text.replace('__DOT__', '.')

        return text


class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies."""

    @abstractmethod
    def chunk(
        self,
        text: str,
        document_id: UUID,
        chunk_token_size: int,
        chunk_overlap: int,
        token_counter: TokenCounter,
    ) -> list[ChunkNode]:
        """Chunk text into semantic units."""
        pass


class FixedTokenChunking(ChunkingStrategy):
    """Fixed token-size chunking strategy.

    Splits text into chunks of approximately chunk_token_size tokens,
    using semantic boundaries where possible.
    """

    def __init__(self, sentence_splitter: SentenceSplitter) -> None:
        self._sentence_splitter = sentence_splitter

    def chunk(
        self,
        text: str,
        document_id: UUID,
        chunk_token_size: int,
        chunk_overlap: int,
        token_counter: TokenCounter,
    ) -> list[ChunkNode]:
        """Split text into fixed-size token chunks."""
        if not text.strip():
            return []

        # Split into semantic units (paragraphs first, then sentences)
        paragraphs = self._split_into_paragraphs(text)
        all_sentences: list[tuple[str, str]] = []  # (sentence, section_title)

        for para in paragraphs:
            section_title = self._extract_section_title(para) if self._is_section_header(para) else ""
            sentences = self._sentence_splitter.split(para)
            for sent in sentences:
                if sent.strip():
                    all_sentences.append((sent, section_title))

        if not all_sentences:
            return []

        # Group sentences into token-sized chunks
        return self._group_into_chunks(
            all_sentences, document_id, chunk_token_size, chunk_overlap, token_counter
        )

    def _split_into_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs."""
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        raw_paragraphs = re.split(r'\n\n+', text)

        paragraphs = []
        for para in raw_paragraphs:
            para = para.strip()
            if not para:
                continue

            # Preserve code blocks and lists as single units
            if para.startswith('```') or para.startswith('    ') or para.startswith('\t'):
                paragraphs.append(para)
                continue

            if re.match(r'^[\s]*[-*+]\s', para) or re.match(r'^[\s]*\d+\.', para):
                paragraphs.append(para)
                continue

            if len(para) < 200 and ('#' in para[:10] or para.startswith('===') or para.startswith('---')):
                paragraphs.append(para)
                continue

            paragraphs.append(para)

        return paragraphs

    def _is_section_header(self, text: str) -> bool:
        """Detect if text is a section header."""
        if text.startswith('#'):
            return True
        if text.startswith('===') or text.startswith('---'):
            return True
        if len(text) < 100 and not text.endswith(('.', '!', '?')):
            return True
        return False

    def _extract_section_title(self, text: str) -> str:
        """Extract clean section title."""
        title = re.sub(r'^#+\s*', '', text)
        title = re.sub(r'^[=\-]+\s*$', '', title)
        return title.strip()

    def _group_into_chunks(
        self,
        sentences: list[tuple[str, str]],
        document_id: UUID,
        chunk_token_size: int,
        chunk_overlap: int,
        token_counter: TokenCounter,
    ) -> list[ChunkNode]:
        """Group sentences into token-sized chunks."""
        if not sentences:
            return []

        chunks: list[ChunkNode] = []
        current_sentences: list[str] = []
        current_token_count = 0
        chunk_index = 0
        previous_section_title = ""
        previous_chunk_text = ""

        for sentence, section_title in sentences:
            sentence_token_count = token_counter.count(sentence)

            # If adding this sentence exceeds target size
            if current_token_count + sentence_token_count > chunk_token_size and current_sentences:
                # Create chunk
                chunk_text = ' '.join(current_sentences)
                section_to_use = previous_section_title

                # Add overlap from previous chunk
                overlap_text = ""
                if previous_chunk_text and chunk_overlap > 0:
                    overlap_text = self._get_overlap_text(previous_chunk_text, chunk_overlap, token_counter)
                    if overlap_text:
                        chunk_text = overlap_text + ' ' + chunk_text
                        # Recalculate token count with overlap
                        current_token_count = token_counter.count(chunk_text)

                chunks.append(
                    self._create_chunk_node(
                        chunk_text,
                        chunk_index,
                        document_id,
                        section_to_use,
                        token_counter.count(chunk_text),
                        overlap_text,
                    )
                )

                # Keep overlap sentences at the start of next chunk
                if chunk_overlap > 0:
                    overlap_sentences = self._get_overlap_sentences(
                        current_sentences, chunk_overlap, token_counter
                    )
                    current_sentences = overlap_sentences
                    current_token_count = sum(token_counter.count(s) for s in overlap_sentences)
                else:
                    current_sentences = []
                    current_token_count = 0

                previous_chunk_text = chunk_text
                chunk_index += 1

            # Add sentence to current chunk
            current_sentences.append(sentence)
            current_token_count += sentence_token_count
            if section_title:
                previous_section_title = section_title

        # Don't forget the last chunk
        if current_sentences:
            chunk_text = ' '.join(current_sentences)

            # Add overlap
            overlap_text = ""
            if previous_chunk_text and chunk_overlap > 0:
                overlap_text = self._get_overlap_text(previous_chunk_text, chunk_overlap, token_counter)
                if overlap_text:
                    chunk_text = overlap_text + ' ' + chunk_text

            chunks.append(
                self._create_chunk_node(
                    chunk_text,
                    chunk_index,
                    document_id,
                    previous_section_title,
                    token_counter.count(chunk_text),
                    overlap_text,
                )
            )

        return chunks

    def _get_overlap_text(
        self, previous_text: str, max_overlap_tokens: int, token_counter: TokenCounter
    ) -> str:
        """Get overlap text from previous chunk."""
        # Calculate approximate char limit based on token ratio
        # Average ~4 chars per token
        max_chars = max_overlap_tokens * 4

        if len(previous_text) <= max_chars:
            return previous_text

        # Try to find a sentence boundary
        overlap_region = previous_text[-max_chars:]
        sentences = self._sentence_splitter.split(overlap_region)

        if len(sentences) > 1:
            return sentences[-1] if sentences else overlap_region

        return overlap_region

    def _get_overlap_sentences(
        self, sentences: list[str], max_overlap_tokens: int, token_counter: TokenCounter
    ) -> list[str]:
        """Get sentences to keep as overlap."""
        overlap_sentences: list[str] = []
        token_count = 0

        for sentence in reversed(sentences):
            sent_tokens = token_counter.count(sentence)
            if token_count + sent_tokens <= max_overlap_tokens:
                overlap_sentences.insert(0, sentence)
                token_count += sent_tokens
            else:
                break

        return overlap_sentences

    def _create_chunk_node(
        self,
        content: str,
        chunk_index: int,
        document_id: UUID,
        section_title: str,
        token_count: int,
        previous_chunk_overlap: str = "",
    ) -> ChunkNode:
        """Create a ChunkNode with all metadata."""
        word_count = len(content.split())
        sentence_count = len(re.findall(r'[.!?]+', content))

        return ChunkNode(
            content=content,
            chunk_index=chunk_index,
            document_id=document_id,
            section_title=section_title,
            paragraph_type=self._detect_paragraph_type(content),
            word_count=word_count,
            sentence_count=sentence_count,
            token_count=token_count,
            chunk_strategy="fixed",
            semantic_boundary_start=True,
            semantic_boundary_end=True,
            previous_chunk_overlap=previous_chunk_overlap,
        )

    def _detect_paragraph_type(self, text: str) -> str:
        """Detect the type of content."""
        text_stripped = text.strip()

        if text_stripped.startswith('```'):
            return 'code'
        if text_stripped.startswith('    ') or text_stripped.startswith('\t'):
            return 'code'
        if re.match(r'^[\s]*[-*+]\s', text_stripped):
            return 'list'
        if re.match(r'^[\s]*\d+\.', text_stripped):
            return 'numbered_list'
        if text_stripped.startswith('#'):
            return 'header'
        if '|' in text_stripped and text_stripped.count('|') >= 2:
            return 'table'
        if text_stripped.startswith('>'):
            return 'quote'

        return 'paragraph'


class RecursiveChunking(ChunkingStrategy):
    """Recursive chunking strategy.

    First splits by large semantic units (paragraphs/sections),
    then recursively breaks down chunks that exceed target size.
    """

    def __init__(self, sentence_splitter: SentenceSplitter) -> None:
        self._sentence_splitter = sentence_splitter
        self._fixed = FixedTokenChunking(sentence_splitter)

    def chunk(
        self,
        text: str,
        document_id: UUID,
        chunk_token_size: int,
        chunk_overlap: int,
        token_counter: TokenCounter,
    ) -> list[ChunkNode]:
        """Recursively chunk text."""
        if not text.strip():
            return []

        # First pass: split into paragraphs
        paragraphs = self._split_into_semantic_units(text)

        # If target size is large, try paragraphs first
        if chunk_token_size >= 512:
            return self._chunk_by_paragraphs(
                paragraphs, document_id, chunk_token_size, chunk_overlap, token_counter
            )

        # For smaller target sizes, use fixed chunking on each paragraph
        all_chunks: list[ChunkNode] = []
        chunk_index = 0
        new_chunks: list[ChunkNode] = []

        for para in paragraphs:
            para_tokens = token_counter.count(para)

            if para_tokens <= chunk_token_size:
                # Paragraph fits in one chunk - create with correct index
                all_chunks.append(
                    self._create_chunk_node(para, chunk_index, document_id, token_counter)
                )
                chunk_index += 1
            else:
                # Paragraph too large, use fixed chunking (returns indexed from 0)
                # Need to re-index the returned chunks
                para_chunks = self._fixed.chunk(
                    para, document_id, chunk_token_size, chunk_overlap, token_counter
                )
                for pc in para_chunks:
                    new_chunks.append(pc)

                # Append re-indexed chunks
                for pc in new_chunks:
                    all_chunks.append(
                        self._create_chunk_node(pc.content, chunk_index, document_id, token_counter)
                    )
                    chunk_index += 1
                new_chunks.clear()

        return all_chunks

    def _split_into_semantic_units(self, text: str) -> list[str]:
        """Split text into semantic units (sections/paragraphs)."""
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Try to split by major sections first (## headers)
        sections = re.split(r'\n(?=##\s)', text)

        if len(sections) <= 1:
            # No major sections, split by paragraphs
            sections = re.split(r'\n\n+', text)

        units = []
        for section in sections:
            section = section.strip()
            if not section:
                continue

            # Within each section, try to split by paragraphs
            paragraphs = re.split(r'\n\n+', section)
            for para in paragraphs:
                para = para.strip()
                if para:
                    units.append(para)

        return units

    def _chunk_by_paragraphs(
        self,
        paragraphs: list[str],
        document_id: UUID,
        chunk_token_size: int,
        chunk_overlap: int,
        token_counter: TokenCounter,
    ) -> list[ChunkNode]:
        """Group paragraphs into chunks."""
        chunks: list[ChunkNode] = []
        current_paragraphs: list[str] = []
        current_tokens = 0
        chunk_index = 0
        previous_section_title = ""

        for para in paragraphs:
            para_tokens = token_counter.count(para)
            section_title = self._extract_section_title(para) if self._is_section_header(para) else ""

            if current_tokens + para_tokens > chunk_token_size and current_paragraphs:
                # Create chunk
                chunk_text = '\n\n'.join(current_paragraphs)
                chunks.append(
                    self._create_chunk_node(chunk_text, chunk_index, document_id, token_counter)
                )
                chunk_index += 1

                # Start new chunk
                current_paragraphs = [para]
                current_tokens = para_tokens
            else:
                current_paragraphs.append(para)
                current_tokens += para_tokens

            if section_title:
                previous_section_title = section_title

        # Last chunk
        if current_paragraphs:
            chunk_text = '\n\n'.join(current_paragraphs)
            chunks.append(
                self._create_chunk_node(chunk_text, chunk_index, document_id, token_counter)
            )

        return chunks

    def _is_section_header(self, text: str) -> bool:
        """Detect if text is a section header."""
        if text.startswith('#'):
            return True
        if text.startswith('===') or text.startswith('---'):
            return True
        if len(text) < 100 and not text.endswith(('.', '!', '?')):
            return True
        return False

    def _extract_section_title(self, text: str) -> str:
        """Extract clean section title."""
        title = re.sub(r'^#+\s*', '', text)
        title = re.sub(r'^[=\-]+\s*$', '', title)
        return title.strip()

    def _create_chunk_node(
        self, content: str, chunk_index: int, document_id: UUID, token_counter: TokenCounter
    ) -> ChunkNode:
        """Create a ChunkNode with all metadata."""
        word_count = len(content.split())
        sentence_count = len(re.findall(r'[.!?]+', content))
        token_count = token_counter.count(content)

        return ChunkNode(
            content=content,
            chunk_index=chunk_index,
            document_id=document_id,
            section_title="",
            paragraph_type=self._detect_paragraph_type(content),
            word_count=word_count,
            sentence_count=sentence_count,
            token_count=token_count,
            chunk_strategy="recursive",
            semantic_boundary_start=True,
            semantic_boundary_end=True,
        )

    def _detect_paragraph_type(self, text: str) -> str:
        """Detect the type of content."""
        text_stripped = text.strip()

        if text_stripped.startswith('```'):
            return 'code'
        if text_stripped.startswith('    ') or text_stripped.startswith('\t'):
            return 'code'
        if re.match(r'^[\s]*[-*+]\s', text_stripped):
            return 'list'
        if re.match(r'^[\s]*\d+\.', text_stripped):
            return 'numbered_list'
        if text_stripped.startswith('#'):
            return 'header'
        if '|' in text_stripped and text_stripped.count('|') >= 2:
            return 'table'
        if text_stripped.startswith('>'):
            return 'quote'

        return 'paragraph'


class TextChunker:
    """Main text chunking class with multiple strategy support.

    Supports:
    - fixed: Fixed token-size chunking
    - recursive: Recursive chunking with semantic boundaries

    Usage:
        settings = ExtractionSettings()
        chunker = TextChunker(settings)
        chunks = chunker.chunk_text(document_text, document_id)
    """

    def __init__(self, settings: ExtractionSettings) -> None:
        self._settings = settings
        self._token_counter = TokenCounter(settings.tokenizer_model)
        self._sentence_splitter = SentenceSplitter()

        # Select strategy
        strategy = settings.chunk_strategy.lower()
        if strategy == "recursive":
            self._strategy: ChunkingStrategy = RecursiveChunking(self._sentence_splitter)
        else:
            # Default to fixed
            self._strategy = FixedTokenChunking(self._sentence_splitter)

    def chunk_text(self, text: str, document_id: UUID) -> list[ChunkNode]:
        """Split text into semantically meaningful chunks.

        Args:
            text: Raw document text.
            document_id: Parent document UUID for linking.

        Returns:
            Ordered list of ChunkNode instances.
        """
        if not text.strip():
            return []

        # Use token-based chunking
        chunks = self._strategy.chunk(
            text,
            document_id,
            self._settings.chunk_token_size,
            self._settings.chunk_overlap,
            self._token_counter,
        )

        logger.debug(
            "Chunked text into %d chunks (strategy=%s, target_tokens=%d, overlap=%d)",
            len(chunks),
            self._settings.chunk_strategy,
            self._settings.chunk_token_size,
            self._settings.chunk_overlap,
        )

        return chunks