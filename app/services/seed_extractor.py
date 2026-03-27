"""Seed Extractor Agent.

Extracts entities, relationships, and potential agent profiles from reality seeds.
Reality seeds can be URLs, documents, or raw text content.
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

import httpx
from langchain_openai import ChatOpenAI

from app.config import OpenAISettings
from app.domain.enums import EntityType, NodeType
from app.domain.nodes import ConceptNode, EntityNode
from app.domain.relationships import GraphRelationship
from app.domain.social.enums import SeedSourceType
from app.domain.social.nodes import SeedNode
from app.exceptions import LLMExtractionError, LLMResponseParsingError

logger = logging.getLogger(__name__)


@dataclass
class ParsedSeedContent:
    """Parsed content from a reality seed."""

    raw_content: str
    content_type: str
    entities: list[str] = field(default_factory=list)
    concepts: list[str] = field(default_factory=list)
    potential_agents: list[dict] = field(default_factory=list)
    relationships: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class SeedExtractionResult:
    """Result of seed extraction."""

    seed_node: SeedNode
    entities: list[EntityNode]
    concepts: list[ConceptNode]
    relationships: list[GraphRelationship]
    potential_agents: list[dict]
    statistics: dict = field(default_factory=dict)


# Prompt templates for seed extraction
SEED_EXTRACTION_SYSTEM = """You are a reality seed extraction engine for social simulation.
Your task is to analyze the given content and extract:

1. **Named Entities**: People, organizations, locations, events, technologies, products
2. **Abstract Concepts**: Topics, ideas, methodologies, themes
3. **Potential Agents**: People who could be simulated as agents (with brief profile hints)
4. **Relationships**: Connections between entities

You MUST respond with valid JSON matching this exact schema:

{
  "entities": [
    {
      "name": "string",
      "entity_type": "PERSON | ORG | LOCATION | EVENT | TECHNOLOGY | PRODUCT | DATE | OTHER",
      "description": "string"
    }
  ],
  "concepts": [
    {
      "name": "string",
      "definition": "string"
    }
  ],
  "potential_agents": [
    {
      "name": "string",
      "context": "string (where they appeared)",
      "role_hints": "string (any role/profession hints)",
      "relationship_context": "string (their social context)"
    }
  ],
  "relationships": [
    {
      "source_name": "string",
      "target_name": "string",
      "relation_type": "MENTIONS | RELATED_TO | BELONGS_TO | DEFINES | KNOWS",
      "weight": 0.0-1.0
    }
  ]
}

Rules:
1. Extract ALL named entities from the content
2. Identify abstract concepts and themes
3. For each person mentioned, consider if they could be a simulation agent
4. Identify relationships between entities
5. Respond ONLY with valid JSON, no markdown"""

SEED_EXTRACTION_USER = """Analyze this reality seed content and extract entities, concepts, potential agents, and relationships:

---
{content}
---

Extract all meaningful information that could help build a social simulation world."""


class SeedExtractorAgent:
    """Agent for extracting structured data from reality seeds.

    This agent:
    1. Fetches content from URLs or processes raw text
    2. Uses LLM to extract entities, concepts, and potential agents
    3. Creates a SeedNode for persistence
    4. Returns structured extraction results

    Args:
        openai_settings: OpenAI API configuration
        http_client: Optional HTTP client for fetching URLs
    """

    def __init__(
        self,
        openai_settings: OpenAISettings,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._llm = ChatOpenAI(
            api_key=openai_settings.api_key,
            base_url=openai_settings.base_url,
            model=openai_settings.model,
            temperature=0.0,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
        self._http_client = http_client
        self._settings = openai_settings

    async def extract_seed(
        self,
        source_url: str | None = None,
        source_type: str = "TEXT",
        raw_content: str = "",
        metadata: dict | None = None,
    ) -> SeedExtractionResult:
        """Extract entities and relationships from a reality seed.

        Args:
            source_url: Optional URL source
            source_type: Type of source (TEXT, URL, DOCUMENT, etc.)
            raw_content: Raw text content
            metadata: Optional metadata

        Returns:
            SeedExtractionResult with extracted data
        """
        # Fetch content if URL provided
        if source_url and source_type == SeedSourceType.URL and not raw_content:
            raw_content = await self._fetch_url_content(source_url)

        # Compute content hash
        content_hash = hashlib.sha256(raw_content.encode()).hexdigest()

        # Parse and extract
        parsed_content = await self._parse_and_extract(raw_content)

        # Create seed node
        seed_node = SeedNode(
            title=metadata.get("title", "Untitled Seed") if metadata else "Untitled Seed",
            source_url=source_url or "",
            content_hash=content_hash,
            source_type=SeedSourceType(source_type),
            raw_content=raw_content,
            filename=metadata.get("filename", "") if metadata else "",
            file_size=len(raw_content.encode()),
            file_type=metadata.get("file_type", "text/plain") if metadata else "text/plain",
        )

        # Build entity nodes
        entities = self._build_entities(parsed_content.entities)

        # Build concept nodes
        concepts = self._build_concepts(parsed_content.concepts)

        # Build relationships
        relationships = self._build_relationships(parsed_content.relationships, entities, concepts)

        # Compute statistics
        statistics = {
            "raw_content_length": len(raw_content),
            "entity_count": len(entities),
            "concept_count": len(concepts),
            "relationship_count": len(relationships),
            "potential_agent_count": len(parsed_content.potential_agents),
        }

        return SeedExtractionResult(
            seed_node=seed_node,
            entities=entities,
            concepts=concepts,
            relationships=relationships,
            potential_agents=parsed_content.potential_agents,
            statistics=statistics,
        )

    async def _fetch_url_content(self, url: str, timeout: int = 30) -> str:
        """Fetch content from a URL.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            Fetched text content
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=timeout)
                response.raise_for_status()
                return response.text
            except httpx.HTTPError as e:
                logger.warning("Failed to fetch URL %s: %s", url, e)
                return ""

    async def _parse_and_extract(self, content: str) -> ParsedSeedContent:
        """Use LLM to parse and extract structured data from content.

        Args:
            content: Raw text content

        Returns:
            ParsedSeedContent with extracted information
        """
        if not content.strip():
            return ParsedSeedContent(raw_content=content, content_type="text")

        try:
            response = await self._llm.ainvoke(
                [
                    {"role": "system", "content": SEED_EXTRACTION_SYSTEM},
                    {"role": "user", "content": SEED_EXTRACTION_USER.format(content=content)},
                ]
            )

            raw_text = response.content
            if not isinstance(raw_text, str):
                raise LLMResponseParsingError("LLM returned non-string content")

            return self._parse_llm_response(raw_text, content)

        except Exception as e:
            logger.warning("Seed extraction failed: %s", e)
            return ParsedSeedContent(raw_content=content, content_type="text")

    def _parse_llm_response(self, raw_json: str, content: str) -> ParsedSeedContent:
        """Parse LLM JSON response into structured data.

        Args:
            raw_json: Raw JSON string from LLM
            content: Original content

        Returns:
            ParsedSeedContent
        """
        import json

        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse LLM JSON: %s", e)
            return ParsedSeedContent(raw_content=content, content_type="text")

        return ParsedSeedContent(
            raw_content=content,
            content_type="text",
            entities=[
                f"{e.get('name', '')} ({e.get('entity_type', 'OTHER')})"
                for e in data.get("entities", [])
            ],
            concepts=[c.get("name", "") for c in data.get("concepts", [])],
            potential_agents=data.get("potential_agents", []),
            relationships=data.get("relationships", []),
            metadata={"extraction_model": self._settings.model},
        )

    def _build_entities(self, entity_strings: list[str]) -> list[EntityNode]:
        """Build EntityNode objects from extracted entity strings.

        Args:
            entity_strings: List of entity strings with types

        Returns:
            List of EntityNode objects
        """
        entities = []
        for entity_str in entity_strings:
            try:
                # Parse "name (TYPE)" format
                if " (" in entity_str and entity_str.endswith(")"):
                    name, type_str = entity_str.rsplit(" (", 1)
                    entity_type_str = type_str.rstrip(")")
                    entity_type = EntityType(entity_type_str) if entity_type_str in [
                        e.value for e in EntityType
                    ] else EntityType.OTHER
                else:
                    name = entity_str
                    entity_type = EntityType.OTHER

                entities.append(
                    EntityNode(
                        name=name.strip(),
                        entity_type=entity_type,
                        description=f"Extracted from reality seed",
                    )
                )
            except Exception as e:
                logger.debug("Failed to parse entity '%s': %s", entity_str, e)
                continue

        return entities

    def _build_concepts(self, concept_names: list[str]) -> list[ConceptNode]:
        """Build ConceptNode objects from concept names.

        Args:
            concept_names: List of concept names

        Returns:
            List of ConceptNode objects
        """
        return [
            ConceptNode(name=name.strip(), definition="Extracted from reality seed")
            for name in concept_names
            if name.strip()
        ]

    def _build_relationships(
        self,
        relationships: list[dict],
        entities: list[EntityNode],
        concepts: list[ConceptNode],
    ) -> list[GraphRelationship]:
        """Build GraphRelationship objects from extracted relationships.

        Args:
            relationships: List of relationship dicts from LLM
            entities: Extracted entity nodes
            concepts: Extracted concept nodes

        Returns:
            List of GraphRelationship objects
        """
        from app.domain.enums import RelationType

        # Build name to ID mapping
        name_to_id: dict[str, UUID] = {}
        for entity in entities:
            name_to_id[entity.name] = entity.id
        for concept in concepts:
            name_to_id[concept.name] = concept.id

        graph_relationships = []
        for rel in relationships:
            source_name = rel.get("source_name", "")
            target_name = rel.get("target_name", "")

            source_id = name_to_id.get(source_name)
            target_id = name_to_id.get(target_name)

            if source_id is None or target_id is None or source_id == target_id:
                continue

            rel_type_str = rel.get("relation_type", "RELATED_TO")
            rel_type = (
                RelationType(rel_type_str)
                if rel_type_str in [r.value for r in RelationType]
                else RelationType.RELATED_TO
            )

            weight = rel.get("weight", 0.5)
            if not isinstance(weight, (int, float)):
                weight = 0.5
            weight = max(0.0, min(1.0, float(weight)))

            graph_relationships.append(
                GraphRelationship(
                    relation_type=rel_type,
                    source_id=source_id,
                    target_id=target_id,
                    weight=weight,
                )
            )

        return graph_relationships
