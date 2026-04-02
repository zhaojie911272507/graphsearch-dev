"""Lineage Path Analyzer using AI.

Analyzes lineage data to generate meaningful titles, descriptions,
and suggest important nodes to highlight.
"""

import logging
from dataclasses import dataclass
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.config import OpenAISettings

logger = logging.getLogger(__name__)


@dataclass
class LineageAnalysisResult:
    """Result of AI analysis of lineage path."""

    title: str
    description: str
    recommended_highlights: list[str]
    summary: str
    key_entities: list[dict]


# Prompt for analyzing lineage paths
LINEAGE_ANALYSIS_SYSTEM = """You are a knowledge graph analyst. Your task is to analyze a data lineage path and create meaningful metadata.

Given a lineage path showing upstream/downstream data flow from a starting node, you need to:
1. Generate a concise, descriptive title (max 50 chars)
2. Write a brief description (max 200 chars) explaining what this lineage represents
3. Identify the most important/interesting nodes to highlight (key entities, concepts, or documents)
4. Provide a one-sentence summary of what this lineage reveals

Focus on:
- What is the main entity or concept being traced?
- What kind of data flow does this show?
- Which nodes are most significant?
"""

LINEAGE_ANALYSIS_HUMAN = """Analyze this lineage path:

Start Node: {start_node_name} ({start_node_type})

Lineage Nodes:
{lineage_nodes}

Lineage Edges (relationships):
{lineage_edges}

Please provide:
1. A title (max 50 characters)
2. A description (max 200 characters)
3. List of node IDs that should be highlighted (most important ones)
4. A one-sentence summary

Respond in JSON format:
{{
    "title": "...",
    "description": "...",
    "highlight_ids": ["id1", "id2", ...],
    "summary": "..."
}}
"""


class LineageAnalyzer:
    """AI-powered lineage path analyzer."""

    def __init__(self, openai_settings: OpenAISettings):
        self.llm = ChatOpenAI(
            model=openai_settings.model,
            temperature=0.3,
            api_key=openai_settings.api_key.get_secret_value() if openai_settings.api_key else None,
            base_url=openai_settings.base_url if openai_settings.base_url else None,
        )

    async def analyze(
        self,
        start_node: dict[str, Any],
        lineage_nodes: list[dict[str, Any]],
        lineage_edges: list[dict[str, Any]],
    ) -> LineageAnalysisResult:
        """Analyze lineage path and generate metadata."""
        try:
            # Prepare node information
            start_node_info = {
                "name": start_node.get("name", start_node.get("title", "Unknown")),
                "type": start_node.get("node_type", start_node.get("type", "Unknown")),
                "id": start_node.get("id", ""),
            }

            # Format nodes for context (limit to first 20 to avoid token limits)
            nodes_context = []
            for i, node in enumerate(lineage_nodes[:20]):
                nodes_context.append(
                    f"- {node.get('name', node.get('title', 'Unknown'))} "
                    f"({node.get('node_type', node.get('type', 'Unknown'))}) "
                    f"[ID: {node.get('id', '')}]"
                )

            # Format edges
            edges_context = []
            for edge in lineage_edges[:15]:
                edges_context.append(
                    f"- {edge.get('source', '?')} --[{edge.get('label', 'RELATED')}]--> {edge.get('target', '?')}"
                )

            prompt = ChatPromptTemplate.from_messages([
                ("system", LINEAGE_ANALYSIS_SYSTEM),
                ("human", LINEAGE_ANALYSIS_HUMAN),
            ])

            response = await self.llm.ainvoke(
                prompt.format(
                    start_node_name=start_node_info["name"],
                    start_node_type=start_node_info["type"],
                    lineage_nodes="\n".join(nodes_context) if nodes_context else "No nodes",
                    lineage_edges="\n".join(edges_context) if edges_context else "No edges",
                )
            )

            # Parse JSON response
            import json
            import re

            # Extract JSON from response
            content = response.content
            json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    result = self._fallback_analysis(start_node_info, lineage_nodes)
            else:
                result = self._fallback_analysis(start_node_info, lineage_nodes)

            return LineageAnalysisResult(
                title=result.get("title", f"Lineage: {start_node_info['name']}")[:50],
                description=result.get("description", "")[:200],
                recommended_highlights=result.get("highlight_ids", [])[:10],
                summary=result.get("summary", ""),
                key_entities=[
                    {"id": n.get("id"), "name": n.get("name", n.get("title", ""))}
                    for n in lineage_nodes[:5]
                ],
            )

        except Exception as e:
            logger.warning(f"Lineage analysis failed, using fallback: {e}")
            return self._fallback_analysis(
                {"name": start_node.get("name", "Unknown"), "type": start_node.get("node_type", "Unknown")},
                lineage_nodes
            )

    def _fallback_analysis(
        self,
        start_node: dict[str, Any],
        lineage_nodes: list[dict[str, Any]],
    ) -> dict:
        """Fallback when AI analysis fails."""
        start_name = start_node.get("name", "Unknown")
        node_count = len(lineage_nodes)

        return {
            "title": f"Data lineage: {start_name}",
            "description": f"Tracing {node_count} related nodes from {start_name}",
            "highlight_ids": [n.get("id") for n in lineage_nodes[:5] if n.get("id")],
            "summary": f"A lineage path with {node_count} related nodes.",
        }