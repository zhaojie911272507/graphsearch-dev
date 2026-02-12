"""Tests for graph relationship domain models."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.enums import RelationType
from app.domain.relationships import GraphRelationship


class TestGraphRelationship:
    """Tests for GraphRelationship creation and validation."""

    def test_create_valid_relationship(self) -> None:
        source = uuid4()
        target = uuid4()
        rel = GraphRelationship(
            relation_type=RelationType.HAS_CHUNK,
            source_id=source,
            target_id=target,
            weight=0.9,
        )
        assert rel.source_id == source
        assert rel.target_id == target
        assert rel.weight == 0.9

    def test_self_loop_rejected(self) -> None:
        node_id = uuid4()
        with pytest.raises(ValidationError, match="Self-loop"):
            GraphRelationship(
                relation_type=RelationType.RELATED_TO,
                source_id=node_id,
                target_id=node_id,
            )

    def test_weight_bounds(self) -> None:
        with pytest.raises(ValidationError):
            GraphRelationship(
                relation_type=RelationType.MENTIONS,
                source_id=uuid4(),
                target_id=uuid4(),
                weight=1.5,  # Out of range
            )

        with pytest.raises(ValidationError):
            GraphRelationship(
                relation_type=RelationType.MENTIONS,
                source_id=uuid4(),
                target_id=uuid4(),
                weight=-0.1,  # Out of range
            )

    def test_neo4j_properties(self) -> None:
        source = uuid4()
        target = uuid4()
        rel = GraphRelationship(
            relation_type=RelationType.RELATED_TO,
            source_id=source,
            target_id=target,
            weight=0.7,
        )
        props = rel.neo4j_properties()
        assert props["source_id"] == str(source)
        assert props["target_id"] == str(target)
        assert props["weight"] == 0.7
        assert props["relation_type"] == "RELATED_TO"

    def test_relationship_is_frozen(self) -> None:
        rel = GraphRelationship(
            relation_type=RelationType.DEFINES,
            source_id=uuid4(),
            target_id=uuid4(),
        )
        with pytest.raises(ValidationError):
            rel.weight = 0.5  # type: ignore[misc]
