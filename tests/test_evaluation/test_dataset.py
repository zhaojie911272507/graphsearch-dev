"""Tests for evaluation dataset loading and filtering (PRD §9.3)."""

import json
from pathlib import Path

import pytest

from app.evaluation.dataset import filter_by_category, filter_by_difficulty, load_dataset


@pytest.fixture
def sample_dataset_file(tmp_path: Path) -> Path:
    """Create a temporary dataset file following PRD §9.3 format."""
    data = {
        "name": "test_dataset",
        "description": "Test dataset for unit tests",
        "cases": [
            {
                "question": "What is Graph RAG?",
                "expected_answer": "Graph RAG combines vector search with knowledge graphs.",
                "expected_contexts": [
                    "Graph RAG combines vector search with knowledge graphs for retrieval."
                ],
                "category": "conceptual",
                "difficulty": "easy",
            },
            {
                "question": "How does traversal work?",
                "expected_answer": "Graph traversal explores neighbors from seed chunks.",
                "expected_contexts": [
                    "Traversal starts from seed chunks and explores neighbors.",
                    "Entities and concepts are discovered via 1-2 hop traversal."
                ],
                "category": "architecture",
                "difficulty": "hard",
            },
        ],
    }
    filepath = tmp_path / "test_qa.json"
    filepath.write_text(json.dumps(data), encoding="utf-8")
    return filepath


class TestLoadDataset:
    def test_load_from_path(self, sample_dataset_file: Path) -> None:
        dataset = load_dataset(sample_dataset_file)
        assert dataset.name == "test_dataset"
        assert len(dataset.cases) == 2
        assert dataset.cases[0].question == "What is Graph RAG?"

    def test_expected_contexts_loaded(self, sample_dataset_file: Path) -> None:
        dataset = load_dataset(sample_dataset_file)
        assert len(dataset.cases[0].expected_contexts) == 1
        assert len(dataset.cases[1].expected_contexts) == 2

    def test_load_nonexistent_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_dataset("/nonexistent/path.json")

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not json", encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid JSON"):
            load_dataset(bad_file)

    def test_case_fields_validated(self, sample_dataset_file: Path) -> None:
        dataset = load_dataset(sample_dataset_file)
        case = dataset.cases[1]
        assert case.category == "architecture"
        assert case.difficulty == "hard"


class TestFilterFunctions:
    def test_filter_by_category(self, sample_dataset_file: Path) -> None:
        dataset = load_dataset(sample_dataset_file)
        filtered = filter_by_category(dataset, "conceptual")
        assert len(filtered.cases) == 1
        assert filtered.cases[0].category == "conceptual"

    def test_filter_by_difficulty(self, sample_dataset_file: Path) -> None:
        dataset = load_dataset(sample_dataset_file)
        filtered = filter_by_difficulty(dataset, "hard")
        assert len(filtered.cases) == 1
        assert filtered.cases[0].difficulty == "hard"

    def test_filter_empty_result(self, sample_dataset_file: Path) -> None:
        dataset = load_dataset(sample_dataset_file)
        filtered = filter_by_category(dataset, "nonexistent")
        assert len(filtered.cases) == 0
