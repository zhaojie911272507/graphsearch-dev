"""Golden dataset generator — cold-start strategy (PRD §9.3).

Uses RAGAS TestsetGenerator to automatically produce Q&A pairs from
ingested business documents, ready for SME review before inclusion
in the golden evaluation dataset.

Workflow:
  1. Load documents (raw text or from Neo4j).
  2. RAGAS builds an internal KnowledgeGraph and generates synthetic
     Q&A pairs with multi-hop and single-hop query distributions.
  3. Output is saved as a golden dataset JSON for SME review.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from langchain_core.documents import Document as LCDocument
from langchain_openai import ChatOpenAI
from ragas.llms import LangchainLLMWrapper
from ragas.testset import TestsetGenerator
from ragas.testset.synthesizers import default_query_distribution

from app.config import OpenAISettings

logger = logging.getLogger(__name__)


async def generate_golden_dataset(
    documents: list[str],
    openai_settings: OpenAISettings,
    *,
    testset_size: int = 100,
    output_path: str | Path = "eval_datasets/golden_qa_generated.json",
    dataset_name: str = "golden_qa_generated",
) -> Path:
    """Generate a golden Q&A dataset from business documents (PRD §9.3).

    Args:
        documents: List of raw document texts to generate Q&A from.
        openai_settings: LLM configuration for generation.
        testset_size: Target number of Q&A pairs (PRD: >= 100).
        output_path: Where to save the generated dataset.
        dataset_name: Name identifier for the dataset.

    Returns:
        Path to the saved JSON file.
    """
    logger.info(
        "Generating golden dataset: %d documents → %d Q&A pairs",
        len(documents),
        testset_size,
    )

    llm = ChatOpenAI(
        api_key=openai_settings.api_key,  # type: ignore[arg-type]
        base_url=openai_settings.base_url,
        model=openai_settings.model,
        temperature=0.3,
    )
    generator_llm = LangchainLLMWrapper(llm)

    lc_docs = [
        LCDocument(page_content=text, metadata={"source": f"doc_{i}"})
        for i, text in enumerate(documents)
    ]

    generator = TestsetGenerator(llm=generator_llm)
    query_distribution = default_query_distribution(generator_llm)

    testset = generator.generate_with_langchain_docs(
        lc_docs,
        testset_size=testset_size,
        query_distribution=query_distribution,
    )

    df = testset.to_pandas()

    cases = []
    for _, row in df.iterrows():
        contexts = row.get("retrieved_contexts") or row.get("contexts") or []
        if isinstance(contexts, str):
            contexts = [contexts]

        cases.append({
            "question": str(row.get("user_input", row.get("question", ""))),
            "expected_answer": str(row.get("reference", row.get("ground_truth", ""))),
            "expected_contexts": [str(c) for c in contexts],
            "category": "auto_generated",
            "difficulty": "medium",
        })

    dataset_payload = {
        "name": dataset_name,
        "description": (
            f"Auto-generated golden dataset from {len(documents)} documents "
            f"using RAGAS TestsetGenerator. Pending SME review (PRD §9.3)."
        ),
        "cases": cases,
        "created_at": datetime.utcnow().isoformat(),
        "sme_reviewed": False,
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(dataset_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info(
        "Golden dataset saved to %s (%d cases, pending SME review)",
        out,
        len(cases),
    )
    return out
