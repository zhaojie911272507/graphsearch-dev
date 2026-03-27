"""AI-powered ontology recommendation service.

Uses LLM to analyze document content and recommend entity types and relation types.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class OntologyRecommendation:
    """Ontology recommendation result."""

    recommended_entity_types: list[dict[str, Any]] = field(default_factory=list)
    recommended_relation_types: list[dict[str, Any]] = field(default_factory=list)
    analysis_summary: str = ""
    confidence_score: float = 0.0
    domain_context: str = ""


class OntologyRecommendationAgent:
    """AI agent for ontology recommendation.

    Analyzes document content using LLM to suggest:
    - Entity types relevant to the domain
    - Relation types between entities
    - Extraction prompts for each type
    """

    def __init__(self, openai_settings: Any):
        """Initialize the recommendation agent.

        Args:
            openai_settings: OpenAI configuration (api_key, base_url, model)
        """
        self._api_key = openai_settings.api_key
        self._base_url = openai_settings.base_url
        self._model = openai_settings.model

    async def analyze_and_recommend(
        self,
        documents: list[dict[str, Any]],
        max_entity_types: int = 10,
        max_relation_types: int = 8,
    ) -> OntologyRecommendation:
        """Analyze documents and recommend ontology.

        Args:
            documents: List of document dicts with 'content' or 'text' field
            max_entity_types: Maximum number of entity types to recommend
            max_relation_types: Maximum number of relation types to recommend

        Returns:
            OntologyRecommendation with suggested types
        """
        # Extract text samples from documents
        text_samples = self._extract_text_samples(documents)

        if not text_samples:
            return OntologyRecommendation(
                analysis_summary="No text content available for analysis",
                confidence_score=0.0,
            )

        # Call LLM for analysis
        recommendation = await self._call_llm_for_recommendation(
            text_samples=text_samples,
            max_entity_types=max_entity_types,
            max_relation_types=max_relation_types,
        )

        return recommendation

    def _extract_text_samples(
        self,
        documents: list[dict[str, Any]],
        max_chars_per_doc: int = 2000,
        max_total_chars: int = 15000,
    ) -> list[str]:
        """Extract text samples from documents for analysis.

        Args:
            documents: List of document dicts
            max_chars_per_doc: Max characters per document
            max_total_chars: Max total characters across all documents

        Returns:
            List of text samples
        """
        samples = []
        total_chars = 0

        for doc in documents:
            if total_chars >= max_total_chars:
                break

            content = doc.get("content") or doc.get("text") or doc.get("raw_content", "")
            if not content:
                continue

            # Take first N characters
            sample = content[:max_chars_per_doc]
            if len(content) > max_chars_per_doc:
                sample += "..."

            samples.append(sample)
            total_chars += len(sample)

        return samples

    async def _call_llm_for_recommendation(
        self,
        text_samples: list[str],
        max_entity_types: int,
        max_relation_types: int,
    ) -> OntologyRecommendation:
        """Call LLM to get ontology recommendations.

        Args:
            text_samples: List of text samples to analyze
            max_entity_types: Max entity types to suggest
            max_relation_types: Max relation types to suggest

        Returns:
            OntologyRecommendation result
        """
        combined_text = "\n\n---\n\n".join(text_samples)

        system_prompt = """You are an expert knowledge engineer specializing in ontology design for knowledge graphs.

Your task is to analyze the provided text documents and recommend:
1. Entity types (classes/concepts) that should exist in the ontology
2. Relation types (properties/relationships) between entities
3. For each type, provide a clear description and extraction prompt

Focus on:
- Domain-specific entities that appear frequently
- Meaningful relationships between entities
- Clear, actionable extraction prompts for LLM-based extraction
- Following best practices in ontology design (clear naming, appropriate granularity)"""

        user_prompt = f"""Analyze the following text samples and recommend an ontology structure.

<TextSamples>
{combined_text}
</TextSamples>

Please provide recommendations in the following JSON format:

```json
{{
    "domain_context": "Brief description of the domain/field these documents belong to",
    "analysis_summary": "2-3 sentence summary of key themes and concepts found",
    "confidence_score": 0.85,
    "recommended_entity_types": [
        {{
            "name": "EntityType",
            "description": "Clear description of what this entity type represents",
            "color": "#3b82f6",
            "icon": "circle",
            "extraction_prompt_template": "Instructions for LLM to extract instances of this entity",
            "example_instances": ["Example1", "Example2"]
        }}
    ],
    "recommended_relation_types": [
        {{
            "name": "RELATION_NAME",
            "description": "What this relationship means",
            "source_types": ["SourceType1"],
            "target_types": ["TargetType1"],
            "directionality": "DIRECTED",
            "extraction_prompt": "Instructions for identifying this relationship"
        }}
    ]
}}
```

Guidelines:
- Recommend 5-{max_entity_types} entity types
- Recommend 3-{max_relation_types} relation types
- Use UPPER_SNAKE_CASE for relation names
- Use PascalCase for entity type names
- Provide practical extraction prompts
- Consider the domain context when naming types"""

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4096,
                }

                async with session.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"LLM API error: {response.status} - {error_text}")
                        return self._get_default_recommendation()

                    result = await response.json()
                    content = result["choices"][0]["message"]["content"]

                    return self._parse_llm_response(content)

        except Exception as e:
            logger.exception(f"LLM recommendation failed: {e}")
            return self._get_default_recommendation()

    def _parse_llm_response(self, content: str) -> OntologyRecommendation:
        """Parse LLM response into OntologyRecommendation.

        Args:
            content: Raw LLM response text

        Returns:
            Parsed OntologyRecommendation
        """
        import json
        import re

        try:
            # Try to extract JSON from the response
            json_match = re.search(r'```json\s*(.+?)\s*```', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r'\{.+?\}', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = content

            data = json.loads(json_str)

            return OntologyRecommendation(
                recommended_entity_types=data.get("recommended_entity_types", []),
                recommended_relation_types=data.get("recommended_relation_types", []),
                analysis_summary=data.get("analysis_summary", "Analysis complete"),
                confidence_score=float(data.get("confidence_score", 0.7)),
                domain_context=data.get("domain_context", "General domain"),
            )

        except Exception as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return self._get_default_recommendation()

    def _get_default_recommendation(self) -> OntologyRecommendation:
        """Return a safe default recommendation when LLM fails."""
        return OntologyRecommendation(
            recommended_entity_types=[
                {
                    "name": "Concept",
                    "description": "Key concepts and ideas mentioned in the text",
                    "color": "#8b5cf6",
                    "icon": "lightbulb",
                    "extraction_prompt_template": "提取文本中的关键概念和核心思想",
                },
                {
                    "name": "Organization",
                    "description": "Companies, institutions, and organizations",
                    "color": "#10b981",
                    "icon": "building",
                    "extraction_prompt_template": "提取文本中提到的公司、机构、组织名称",
                },
                {
                    "name": "Person",
                    "description": "Names of people mentioned in the text",
                    "color": "#f59e0b",
                    "icon": "user",
                    "extraction_prompt_template": "提取文本中提到的人名",
                },
            ],
            recommended_relation_types=[
                {
                    "name": "MENTIONS",
                    "description": "Text mentions or references an entity",
                    "source_types": ["Document", "Chunk"],
                    "target_types": ["Concept", "Organization", "Person"],
                    "directionality": "DIRECTED",
                },
                {
                    "name": "RELATED_TO",
                    "description": "General association between entities",
                    "source_types": ["Concept", "Organization", "Person"],
                    "target_types": ["Concept", "Organization", "Person"],
                    "directionality": "UNDIRECTED",
                },
            ],
            analysis_summary="Default recommendation based on general patterns. Run full analysis for domain-specific suggestions.",
            confidence_score=0.5,
            domain_context="General",
        )

    async def analyze_domain_with_context(
        self,
        domain_key: str,
        existing_entity_types: list[dict[str, Any]],
        existing_relation_types: list[dict[str, Any]],
        documents: list[dict[str, Any]],
        max_recommendations: int = 5,
    ) -> OntologyRecommendation:
        """Analyze and recommend with awareness of existing ontology.

        This method considers existing types to avoid duplicates
        and suggests complementary additions.

        Args:
            domain_key: Domain identifier
            existing_entity_types: Current entity types in the domain
            existing_relation_types: Current relation types in the domain
            documents: Documents to analyze
            max_recommendations: Max new types to recommend

        Returns:
            OntologyRecommendation with complementary suggestions
        """
        base_recommendation = await self.analyze_and_recommend(documents)

        # Filter out existing types
        existing_entity_names = {t.get("name") for t in existing_entity_types}
        existing_relation_names = {t.get("name") for t in existing_relation_types}

        new_entity_types = [
            t for t in base_recommendation.recommended_entity_types
            if t.get("name") not in existing_entity_names
        ][:max_recommendations]

        new_relation_types = [
            t for t in base_recommendation.recommended_relation_types
            if t.get("name") not in existing_relation_names
        ][:max_recommendations]

        return OntologyRecommendation(
            recommended_entity_types=new_entity_types,
            recommended_relation_types=new_relation_types,
            analysis_summary=base_recommendation.analysis_summary + " (Filtered for new suggestions only)",
            confidence_score=base_recommendation.confidence_score,
            domain_context=base_recommendation.domain_context,
        )
