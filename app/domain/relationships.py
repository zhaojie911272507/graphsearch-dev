"""Graph relationship (edge) domain models.

All relationships are directed, typed, and carry a weight property.
Referential integrity is enforced at the model level via required
source_id / target_id fields.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import RelationType


class GraphRelationship(BaseModel):
    """A typed, weighted, directed edge between two graph nodes.

    Attributes:
        id: Unique relationship identifier.
        relation_type: The semantic type of the relationship.
        source_id: UUID of the source node.
        target_id: UUID of the target node.
        weight: Confidence / relevance weight in [0.0, 1.0].
        properties: Optional extra properties for the edge.
    """

    model_config = ConfigDict(frozen=True)

    id: UUID = Field(default_factory=uuid4)
    relation_type: RelationType
    source_id: UUID
    target_id: UUID
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    properties: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_no_self_loop(self) -> "GraphRelationship":
        """Prevent self-referencing edges."""
        if self.source_id == self.target_id:
            msg = f"Self-loop detected: source_id and target_id are both {self.source_id}"
            raise ValueError(msg)
        return self

    def neo4j_properties(self) -> dict[str, object]:
        """Serialize to a flat dict for Neo4j parameterized queries.

        Returns:
            Property map with string-keyed primitive values.
        """
        props: dict[str, object] = {
            "id": str(self.id),
            "relation_type": self.relation_type.value,
            "source_id": str(self.source_id),
            "target_id": str(self.target_id),
            "weight": self.weight,
        }
        props.update(self.properties)
        return props
