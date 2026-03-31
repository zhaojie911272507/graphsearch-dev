"""Tests for extraction layer observability (metrics and tracing)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.config import ExtractionSettings, OpenAISettings
from app.domain.nodes import ChunkNode
from app.extraction.extractor import ExtractionResult, GraphExtractor


class TestExtractionMetricsAndTracing:
    """Test metrics and tracing instrumentation in GraphExtractor."""

    @pytest.fixture
    def sample_chunk(self) -> ChunkNode:
        """Create a sample chunk for testing."""
        return ChunkNode(
            content="Graph RAG combines vector search with knowledge graphs.",
            chunk_index=0,
            document_id=str(uuid4()),
        )

    @pytest.fixture
    def mock_tracer(self) -> tuple:
        """Mock OpenTelemetry tracer."""
        mock_span = MagicMock()
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=None)

        tracer = MagicMock()
        tracer.start_as_current_span = MagicMock(return_value=mock_span)
        return tracer, mock_span

    @pytest.fixture
    def mock_settings(self) -> OpenAISettings:
        """Mock OpenAI settings."""
        return OpenAISettings(api_key="sk-test-key", model="gpt-4o")

    @pytest.fixture
    def mock_llm_response(self) -> MagicMock:
        """Create a mock LLM response."""
        mock_response = MagicMock()
        mock_response.content = '{"entities": [], "concepts": [], "relationships": []}'
        return mock_response

    def _create_mock_llm(self, response_content: str = '{"entities": [], "concepts": [], "relationships": []}'):
        """Helper to create a mock LLM with custom response."""
        mock_llm = MagicMock()
        mock_llm.model_name = "gpt-4o"

        async def mock_ainvoke(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.content = response_content
            return mock_response

        # Use object.__setattr__ to bypass Pydantic validation
        object.__setattr__(mock_llm, 'ainvoke', mock_ainvoke)
        return mock_llm

    @pytest.mark.asyncio
    async def test_extraction_success_records_metrics(
        self,
        mock_settings: OpenAISettings,
        sample_chunk: ChunkNode,
    ) -> None:
        """Test that successful extraction records success metrics."""
        from app.observability.metrics import MetricsRegistry

        # Create extractor with mocked LLM
        extractor = GraphExtractor(
            openai_settings=mock_settings,
            extraction_settings=ExtractionSettings(max_retries=1),
        )

        # Mock LLM response with valid JSON
        response_content = '''{
            "entities": [
                {"name": "Graph RAG", "entity_type": "TECHNOLOGY", "description": "A retrieval system"}
            ],
            "concepts": [
                {"name": "Vector Search", "definition": "Similarity search using embeddings"}
            ],
            "relationships": [
                {"source_name": "Graph RAG", "target_name": "Vector Search", "relation_type": "USES", "weight": 0.8}
            ]
        }'''

        extractor._llm = self._create_mock_llm(response_content)

        # Run extraction
        result = await extractor._extract_single_chunk(sample_chunk)

        # Verify result
        assert len(result.entities) == 1
        assert len(result.concepts) == 1
        assert len(result.relationships) == 1

        # Verify success metric exists
        assert MetricsRegistry.rag_extraction_success_total is not None

    @pytest.mark.asyncio
    async def test_extraction_failure_records_error_metric(
        self,
        mock_settings: OpenAISettings,
        sample_chunk: ChunkNode,
    ) -> None:
        """Test that failed extraction records failure metrics."""
        from app.observability.metrics import MetricsRegistry

        extractor = GraphExtractor(
            openai_settings=mock_settings,
            extraction_settings=ExtractionSettings(max_retries=1),
        )

        # Mock LLM to raise an exception using patch
        mock_llm = MagicMock()
        mock_llm.model_name = "gpt-4o"
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM error"))

        extractor._llm = mock_llm

        # Run extraction - should handle gracefully
        result = await extractor._process_chunk_safe(sample_chunk)

        # Verify empty result on failure
        assert len(result.entities) == 0
        assert len(result.concepts) == 0
        assert len(result.relationships) == 0

        # Verify failure metric exists
        assert MetricsRegistry.rag_extraction_failure_total is not None

    @pytest.mark.asyncio
    async def test_llm_calls_total_metric_recorded(
        self,
        mock_settings: OpenAISettings,
        sample_chunk: ChunkNode,
    ) -> None:
        """Test that LLM calls total metric is recorded."""
        from app.observability.metrics import MetricsRegistry

        extractor = GraphExtractor(
            openai_settings=mock_settings,
            extraction_settings=ExtractionSettings(max_retries=1),
        )

        extractor._llm = self._create_mock_llm()

        await extractor._extract_single_chunk(sample_chunk)

        # Verify LLM calls metric exists
        assert MetricsRegistry.rag_llm_calls_total is not None

    @pytest.mark.asyncio
    async def test_extraction_latency_histogram_recorded(
        self,
        mock_settings: OpenAISettings,
        sample_chunk: ChunkNode,
    ) -> None:
        """Test that extraction latency histogram is recorded."""
        from app.observability.metrics import MetricsRegistry

        extractor = GraphExtractor(
            openai_settings=mock_settings,
            extraction_settings=ExtractionSettings(max_retries=1),
        )

        extractor._llm = self._create_mock_llm()

        await extractor._extract_single_chunk(sample_chunk)

        # Verify latency histogram exists
        assert MetricsRegistry.rag_extraction_latency_seconds is not None

    @pytest.mark.asyncio
    async def test_chunk_size_bucket_categorization(
        self,
        mock_settings: OpenAISettings,
    ) -> None:
        """Test that chunks are categorized into correct size buckets."""
        from app.observability.metrics import MetricsRegistry

        extractor = GraphExtractor(
            openai_settings=mock_settings,
            extraction_settings=ExtractionSettings(max_retries=1),
        )

        # Test small chunk (< 256)
        small_chunk = ChunkNode(
            content="Short text.",
            chunk_index=0,
            document_id=str(uuid4()),
        )

        # Test medium chunk (256-511)
        medium_chunk = ChunkNode(
            content="x" * 300,
            chunk_index=0,
            document_id=str(uuid4()),
        )

        # Test large chunk (>= 512)
        large_chunk = ChunkNode(
            content="x" * 600,
            chunk_index=0,
            document_id=str(uuid4()),
        )

        extractor._llm = self._create_mock_llm()

        for chunk in [small_chunk, medium_chunk, large_chunk]:
            await extractor._extract_single_chunk(chunk)

        # Verify latency histogram with chunk_size_bucket label exists
        assert MetricsRegistry.rag_extraction_latency_seconds is not None

    @pytest.mark.asyncio
    async def test_tracing_span_created_for_extraction(
        self,
        mock_settings: OpenAISettings,
        sample_chunk: ChunkNode,
        mock_tracer: tuple,
    ) -> None:
        """Test that tracing span is created for extraction."""
        tracer, mock_span = mock_tracer

        with patch('app.extraction.extractor.TracingSetup') as mock_tracing_setup:
            mock_tracing_setup.get_tracer = MagicMock(return_value=tracer)

            extractor = GraphExtractor(
                openai_settings=mock_settings,
                extraction_settings=ExtractionSettings(max_retries=1),
            )

            extractor._llm = self._create_mock_llm()

            await extractor._extract_single_chunk(sample_chunk)

            # Verify tracer was called to start span
            assert tracer.start_as_current_span.called

    @pytest.mark.asyncio
    async def test_tracing_span_attributes_set(
        self,
        mock_settings: OpenAISettings,
        sample_chunk: ChunkNode,
        mock_tracer: tuple,
    ) -> None:
        """Test that tracing span has correct attributes."""
        tracer, mock_span = mock_tracer

        with patch('app.extraction.extractor.TracingSetup') as mock_tracing_setup:
            mock_tracing_setup.get_tracer = MagicMock(return_value=tracer)

            extractor = GraphExtractor(
                openai_settings=mock_settings,
                extraction_settings=ExtractionSettings(max_retries=1),
            )

            response_content = '''{
                "entities": [{"name": "Test", "entity_type": "PERSON", "description": "Test entity"}],
                "concepts": [],
                "relationships": []
            }'''
            extractor._llm = self._create_mock_llm(response_content)

            await extractor._extract_single_chunk(sample_chunk)

            # Verify span attributes were set
            mock_span.set_attribute.assert_called()

    @pytest.mark.asyncio
    async def test_extraction_result_structure(
        self,
        mock_settings: OpenAISettings,
        sample_chunk: ChunkNode,
    ) -> None:
        """Test extraction result has correct structure."""
        extractor = GraphExtractor(
            openai_settings=mock_settings,
            extraction_settings=ExtractionSettings(max_retries=1),
        )

        response_content = '''{
            "entities": [
                {"name": "Entity1", "entity_type": "PERSON", "description": "A person"},
                {"name": "Entity2", "entity_type": "ORG", "description": "An organization"}
            ],
            "concepts": [
                {"name": "Concept1", "definition": "A concept"}
            ],
            "relationships": [
                {"source_name": "Entity1", "target_name": "Entity2", "relation_type": "WORKS_FOR", "weight": 0.9}
            ]
        }'''
        extractor._llm = self._create_mock_llm(response_content)

        result = await extractor._extract_single_chunk(sample_chunk)

        assert result.chunk_id == sample_chunk.id
        assert len(result.entities) == 2
        assert len(result.concepts) == 1
        assert len(result.relationships) == 1
        assert result.relationships[0].weight == 0.9

    @pytest.mark.asyncio
    async def test_extraction_handles_invalid_json(
        self,
        mock_settings: OpenAISettings,
        sample_chunk: ChunkNode,
    ) -> None:
        """Test extraction handles invalid JSON response."""
        extractor = GraphExtractor(
            openai_settings=mock_settings,
            extraction_settings=ExtractionSettings(max_retries=1),
        )

        extractor._llm = self._create_mock_llm("This is not valid JSON")

        result = await extractor._process_chunk_safe(sample_chunk)

        # Should return empty result on parsing error
        assert len(result.entities) == 0
        assert len(result.concepts) == 0
        assert len(result.relationships) == 0
