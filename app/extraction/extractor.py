"""Graph entity and relationship extractor using LLM.

Processes text chunks concurrently with semaphore-based rate limiting
and implements retry-with-graceful-degradation for LLM failures.

Supports cross-document entity deduplication by name + entity_type.
"""

import asyncio
import hashlib
import json
import logging
import uuid
from uuid import UUID

from langchain_openai import ChatOpenAI

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
        domain_context: dict | None = None,  # New parameter for domain context
    ) -> list[ExtractionResult]:
        """Process multiple chunks concurrently with rate limiting.

        Args:
            chunks: Text chunks to extract entities/relationships from.
            domain_context: Optional domain context with custom extraction prompt.

        Returns:
            List of ExtractionResult, one per chunk (may be empty on failure).
        """
        tasks = [self._process_chunk_with_semaphore(chunk, domain_context) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results

    async def _process_chunk_with_semaphore(
        self,
        chunk: ChunkNode,
        domain_context: dict | None = None,  # New parameter
    ) -> ExtractionResult:
        """Acquire semaphore and process a single chunk."""
        async with self._semaphore:
            return await self._process_chunk_safe(chunk, domain_context)

    async def _process_chunk_safe(
        self,
        chunk: ChunkNode,
        domain_context: dict | None = None,  # New parameter
    ) -> ExtractionResult:
        """Process chunk with retry and graceful degradation.

        On exhausted retries, returns an empty ExtractionResult
        rather than propagating the exception.
        """
        try:
            return await self._process_chunk_with_retry(chunk, domain_context)
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

    async def _process_chunk_with_retry(
        self,
        chunk: ChunkNode,
        domain_context: dict | None = None,  # New parameter
    ) -> ExtractionResult:
        """Single chunk extraction with retry logic.

        Raises:
            LLMExtractionError: If the LLM call itself fails.
            LLMResponseParsingError: If the response cannot be parsed.
        """
        # Manual retry loop with exponential backoff using configured max_retries
        from tenacity import wait_exponential

        wait = wait_exponential(multiplier=1, min=1, max=10)
        last_exception: Exception | None = None
        retry_state = {"attempt": 0}

        for attempt in range(1, self._max_retries + 1):
            try:
                retry_state["attempt"] = attempt
                return await self._extract_single_chunk(chunk, domain_context)
            except (LLMExtractionError, LLMResponseParsingError) as e:
                last_exception = e
                if attempt < self._max_retries:
                    await asyncio.sleep(wait(retry_state))

        # All attempts failed
        if last_exception:
            raise last_exception
        return await self._extract_single_chunk(chunk, domain_context)

    async def _extract_single_chunk(
        self,
        chunk: ChunkNode,
        domain_context: dict | None = None,  # New parameter
    ) -> ExtractionResult:
        """Call LLM and parse the response into domain models."""
        # Use domain-specific prompt if available
        prompt_system = ENTITY_EXTRACTION_SYSTEM
        if domain_context:
            custom_prompt = domain_context.get("extraction_prompt_template")
            if custom_prompt:
                prompt_system = custom_prompt

        prompt_user = ENTITY_EXTRACTION_USER.format(chunk_content=chunk.content)

        try:
            response = await self._llm.ainvoke(
                [
                    {"role": "system", "content": prompt_system},
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

            entity_name = raw_entity.get("name", "Unknown")
            description = raw_entity.get("description", "")

            # Generate deterministic UUID based on name + entity_type for deduplication
            # This ensures the same entity name across documents gets the same UUID
            dedup_key = f"{entity_name}|{entity_type.value}"
            entity_id = UUID(hex=hashlib.md5(dedup_key.encode()).hexdigest())

            entity = EntityNode(
                id=entity_id,
                name=entity_name,
                entity_type=entity_type,
                description=description,
                reference_count=1,
                source_document_ids=[],  # Will be populated by caller
            )
            entities.append(entity)
            name_to_id[entity_name] = entity_id

        # Parse concepts
        for raw_concept in data.get("concepts", []):
            concept_name = raw_concept.get("name", "Unknown")
            definition = raw_concept.get("definition", "")

            # Generate deterministic UUID based on name for deduplication
            concept_id = UUID(hex=hashlib.md5(concept_name.encode()).hexdigest())

            concept = ConceptNode(
                id=concept_id,
                name=concept_name,
                definition=definition,
                reference_count=1,
                source_document_ids=[],  # Will be populated by caller
            )
            concepts.append(concept)
            name_to_id[concept_name] = concept_id

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
