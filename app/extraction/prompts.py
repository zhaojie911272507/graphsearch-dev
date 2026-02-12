"""Prompt templates for LLM-based graph extraction.

Structured to produce JSON output that maps directly to our Pydantic
domain models (EntityNode, ConceptNode, GraphRelationship).
"""

ENTITY_EXTRACTION_SYSTEM = """You are a knowledge graph extraction engine.
Given a text chunk, extract all named entities and abstract concepts.
Also identify relationships between them.

You MUST respond with valid JSON matching this exact schema:

{
  "entities": [
    {
      "name": "string (entity name)",
      "entity_type": "PERSON | ORG | LOCATION | EVENT | TECHNOLOGY | PRODUCT | DATE | OTHER",
      "description": "string (brief description)"
    }
  ],
  "concepts": [
    {
      "name": "string (concept name)",
      "definition": "string (brief definition)"
    }
  ],
  "relationships": [
    {
      "source_name": "string (entity or concept name)",
      "target_name": "string (entity or concept name)",
      "relation_type": "MENTIONS | RELATED_TO | BELONGS_TO | DEFINES",
      "weight": 0.0-1.0
    }
  ]
}

Rules:
1. Extract ALL meaningful entities (people, organizations, technologies, etc.).
2. Extract abstract CONCEPTS (topics, theories, methodologies).
3. Identify relationships BETWEEN extracted entities/concepts.
4. Use the exact entity_type and relation_type values listed above.
5. weight reflects confidence (1.0 = certain, 0.5 = possible).
6. Respond ONLY with JSON. No markdown, no explanation."""

ENTITY_EXTRACTION_USER = """Extract entities, concepts, and relationships from this text chunk:

---
{chunk_content}
---"""
