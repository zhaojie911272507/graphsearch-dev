"""Graph entity and relationship extractor using LLM.

Processes text chunks concurrently with semaphore-based rate limiting
and implements retry-with-graceful-degradation for LLM failures.
"""

import asyncio
import json
import logging
from uuid import UUID

from langchain_openai import ChatOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import ExtractionSettings, OpenAISettings
from app.domain.enums import EntityType, RelationType
from app.domain.nodes import ChunkNode, ConceptNode, EntityNode
from app.domain.relationships import GraphRelationship
from app.exceptions import LLMExtractionError, LLMResponseParsingError
from app.extraction.prompts import ENTITY_EXTRACTION_SYSTEM, ENTITY_EXTRACTION_USER

logger = logging.getLogger(__name__)


class ExtractionResult:
    """Container for the results of processing a single chunk."""

    __slots__ = ("chunk_id", "entities", "concepts", "relationships")

    def __init__(
        self,
        chunk_id: UUID,
        entities: list[EntityNode],
        concepts: list[ConceptNode],
        relationships: list[GraphRelationship],
    ) -> None:
        self.chunk_id = chunk_id
        self.entities = entities
        self.concepts = concepts
        self.relationships = relationships


class GraphExtractor:
    """Extracts structured graph data from text chunks using an LLM.

    Features:
    - Concurrent chunk processing with asyncio.Semaphore.
    - Retry (2x) with exponential backoff per chunk.
    - Graceful degradation: returns empty result on exhausted retries.
    - Strict Pydantic validation on LLM output.

    Args:
        openai_settings: LLM API configuration.
        extraction_settings: Concurrency and retry configuration.
    """

    def __init__(
        self,
        openai_settings: OpenAISettings,
        extraction_settings: ExtractionSettings,
    ) -> None:
        self._llm = ChatOpenAI(
            api_key=openai_settings.api_key,  # type: ignore[arg-type]
            base_url=openai_settings.base_url,
            model=openai_settings.model,
            temperature=0.0,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
        self._semaphore = asyncio.Semaphore(extraction_settings.max_concurrency)
        self._max_retries = extraction_settings.max_retries

    async def extract_from_chunks(
        self,
        chunks: list[ChunkNode],
    ) -> list[ExtractionResult]:
        """Process multiple chunks concurrently with rate limiting.

        Args:
            chunks: Text chunks to extract entities/relationships from.

        Returns:
            List of ExtractionResult, one per chunk (may be empty on failure).
        """
        tasks = [self._process_chunk_with_semaphore(chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results

    async def _process_chunk_with_semaphore(
        self,
        chunk: ChunkNode,
    ) -> ExtractionResult:
        """Acquire semaphore and process a single chunk."""
        async with self._semaphore:
            return await self._process_chunk_safe(chunk)

    async def _process_chunk_safe(
        self,
        chunk: ChunkNode,
    ) -> ExtractionResult:
        """Process chunk with retry and graceful degradation.

        On exhausted retries, returns an empty ExtractionResult
        rather than propagating the exception.
        """
        try:
            return await self._process_chunk_with_retry(chunk)
        except (LLMExtractionError, LLMResponseParsingError) as exc:
            logger.warning(
                "Extraction failed after retries for chunk %s: %s",
                chunk.id,
                exc.message,
            )
            return ExtractionResult(
                chunk_id=chunk.id,
                entities=[],
                concepts=[],
                relationships=[],
            )

    @retry(
        retry=retry_if_exception_type((LLMExtractionError, LLMResponseParsingError)),
        stop=stop_after_attempt(3),  # 1 initial + 2 retries
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _process_chunk_with_retry(
        self,
        chunk: ChunkNode,
    ) -> ExtractionResult:
        """Single chunk extraction with retry logic.

        Raises:
            LLMExtractionError: If the LLM call itself fails.
            LLMResponseParsingError: If the response cannot be parsed.
        """
        return await self._extract_single_chunk(chunk)

    async def _extract_single_chunk(
        self,
        chunk: ChunkNode,
    ) -> ExtractionResult:
        """Call LLM and parse the response into domain models."""
        prompt_user = ENTITY_EXTRACTION_USER.format(chunk_content=chunk.content)

        try:
            response = await self._llm.ainvoke(
                [
                    {"role": "system", "content": ENTITY_EXTRACTION_SYSTEM},
                    {"role": "user", "content": prompt_user},
                ]
            )
        except Exception as exc:
            raise LLMExtractionError(
                f"LLM invocation failed: {exc}",
                details={"chunk_id": str(chunk.id)},
            ) from exc

        raw_text = response.content
        if not isinstance(raw_text, str):
            raise LLMResponseParsingError(
                "LLM returned non-string content",
                details={"chunk_id": str(chunk.id), "type": type(raw_text).__name__},
            )

        return self._parse_llm_response(raw_text, chunk.id)

    def _parse_llm_response(
        self,
        raw_json: str,
        chunk_id: UUID,
    ) -> ExtractionResult:
        """Parse LLM JSON output into typed domain objects.

        Args:
            raw_json: Raw JSON string from LLM.
            chunk_id: The source chunk UUID.

        Returns:
            Validated ExtractionResult.

        Raises:
            LLMResponseParsingError: On malformed JSON or invalid fields.
        """
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise LLMResponseParsingError(
                f"Invalid JSON from LLM: {exc}",
                details={"chunk_id": str(chunk_id), "raw": raw_json[:500]},
            ) from exc

        entities: list[EntityNode] = []
        concepts: list[ConceptNode] = []
        name_to_id: dict[str, UUID] = {}

        # Parse entities
        for raw_entity in data.get("entities", []):
            try:
                entity_type = EntityType(raw_entity.get("entity_type", "OTHER"))
            except ValueError:
                entity_type = EntityType.OTHER

            entity = EntityNode(
                name=raw_entity.get("name", "Unknown"),
                entity_type=entity_type,
                description=raw_entity.get("description", ""),
            )
            entities.append(entity)
            name_to_id[entity.name] = entity.id

        # Parse concepts
        for raw_concept in data.get("concepts", []):
            concept = ConceptNode(
                name=raw_concept.get("name", "Unknown"),
                definition=raw_concept.get("definition", ""),
            )
            concepts.append(concept)
            name_to_id[concept.name] = concept.id

        # Parse relationships (only if both endpoints exist)
        relationships: list[GraphRelationship] = []
        for raw_rel in data.get("relationships", []):
            source_name = raw_rel.get("source_name", "")
            target_name = raw_rel.get("target_name", "")

            source_id = name_to_id.get(source_name)
            target_id = name_to_id.get(target_name)

            if source_id is None or target_id is None:
                logger.debug(
                    "Skipping relationship: endpoint not found (%s -> %s)",
                    source_name,
                    target_name,
                )
                continue

            if source_id == target_id:
                continue

            try:
                rel_type = RelationType(raw_rel.get("relation_type", "RELATED_TO"))
            except ValueError:
                rel_type = RelationType.RELATED_TO

            weight = raw_rel.get("weight", 0.5)
            if not isinstance(weight, (int, float)):
                weight = 0.5
            weight = max(0.0, min(1.0, float(weight)))

            relationships.append(
                GraphRelationship(
                    relation_type=rel_type,
                    source_id=source_id,
                    target_id=target_id,
                    weight=weight,
                )
            )

        logger.debug(
            "Extracted from chunk %s: %d entities, %d concepts, %d relationships",
            chunk_id,
            len(entities),
            len(concepts),
            len(relationships),
        )

        return ExtractionResult(
            chunk_id=chunk_id,
            entities=entities,
            concepts=concepts,
            relationships=relationships,
        )
