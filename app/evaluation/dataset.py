"""Golden evaluation dataset management (PRD §9.3).

Handles loading, validating, and filtering golden Q&A datasets.
Dataset format: [question, expected_answer, expected_contexts].
"""

import json
import logging
from pathlib import Path

from app.evaluation.schemas import EvalCase, EvalDataset

logger = logging.getLogger(__name__)

_DEFAULT_DATASET_DIR = Path(__file__).resolve().parent.parent.parent / "eval_datasets"


def load_dataset(
    path: str | Path | None = None,
    *,
    dataset_dir: Path = _DEFAULT_DATASET_DIR,
) -> EvalDataset:
    """Load an evaluation dataset from a JSON file.

    Args:
        path: Explicit path to JSON file.  If None, loads
              ``eval_datasets/golden_qa.json``.
        dataset_dir: Base directory when *path* is a relative filename.

    Raises:
        FileNotFoundError: If the dataset file does not exist.
        ValueError: If the JSON is malformed or fails validation.
    """
    if path is None:
        resolved = dataset_dir / "golden_qa.json"
    else:
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = dataset_dir / resolved

    if not resolved.exists():
        raise FileNotFoundError(f"Dataset file not found: {resolved}")

    raw_text = resolved.read_text(encoding="utf-8")
    try:
        raw_data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in dataset file {resolved}: {exc}") from exc

    cases = [EvalCase(**item) for item in raw_data.get("cases", [])]

    dataset = EvalDataset(
        name=raw_data.get("name", resolved.stem),
        description=raw_data.get("description", ""),
        cases=cases,
    )

    logger.info(
        "Loaded evaluation dataset '%s' with %d cases from %s",
        dataset.name,
        len(dataset.cases),
        resolved,
    )
    return dataset


def filter_by_category(dataset: EvalDataset, category: str) -> EvalDataset:
    """Return a new dataset containing only cases of the given category."""
    filtered = [c for c in dataset.cases if c.category == category]
    return EvalDataset(
        name=f"{dataset.name}[{category}]",
        description=dataset.description,
        cases=filtered,
    )


def filter_by_difficulty(dataset: EvalDataset, difficulty: str) -> EvalDataset:
    """Return a new dataset containing only cases of the given difficulty."""
    filtered = [c for c in dataset.cases if c.difficulty == difficulty]
    return EvalDataset(
        name=f"{dataset.name}[{difficulty}]",
        description=dataset.description,
        cases=filtered,
    )
