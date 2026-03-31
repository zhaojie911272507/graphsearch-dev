"""Tests for ontology management API endpoints (entity types, relation types, versioning).

Covers:
- Entity type CRUD operations
- Relation type CRUD operations
- Ontology versioning and diffs
- Audit logging integration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(mock_graph_store):
    """Create FastAPI test client with mocked graph store."""
    app.state.graph_store = mock_graph_store
    return TestClient(app)


@pytest.fixture
def mock_graph_store():
    """Mock GraphStore for ontology management operations."""
    store = AsyncMock()

    # Entity types
    store.get_entity_types = AsyncMock(return_value=[
        {
            "name": "PERSON",
            "description": "A person",
            "color": "#58a6ff",
            "icon": "user",
            "is_builtin": True,
            "created_at": "2026-03-26T00:00:00Z",
            "updated_at": "2026-03-26T00:00:00Z",
        },
        {
            "name": "CustomEntity",
            "description": "A custom entity",
            "color": "#7ee787",
            "icon": "tag",
            "is_builtin": False,
            "created_at": "2026-03-26T00:00:00Z",
            "updated_at": "2026-03-26T00:00:00Z",
            "extraction_prompt_template": "Extract custom entities...",
        },
    ])
    store.count_entity_instances = AsyncMock(return_value=10)
    store.get_entity_type_by_name = AsyncMock(return_value={
        "name": "CustomEntity",
        "description": "A custom entity",
        "color": "#7ee787",
        "icon": "tag",
        "is_builtin": False,
        "created_at": "2026-03-26T00:00:00Z",
        "updated_at": "2026-03-26T00:00:00Z",
        "extraction_prompt_template": "Extract custom entities...",
    })
    store.create_entity_type = AsyncMock(return_value={
        "name": "NewEntity",
        "description": "A new entity",
        "color": "#ff7b72",
        "icon": "plus",
        "is_builtin": False,
        "created_at": "2026-03-26T00:00:00Z",
        "updated_at": "2026-03-26T00:00:00Z",
        "extraction_prompt_template": "Extract new entities...",
    })
    store.update_entity_type = AsyncMock(return_value={
        "name": "CustomEntity",
        "description": "Updated description",
        "color": "#7ee787",
        "icon": "tag",
        "is_builtin": False,
        "created_at": "2026-03-26T00:00:00Z",
        "updated_at": "2026-03-26T01:00:00Z",
        "extraction_prompt_template": "Updated template...",
    })
    store.delete_entity_type = AsyncMock(return_value=None)

    # Relation types
    store.get_relation_types = AsyncMock(return_value=[
        {
            "name": "RELATED_TO",
            "description": "Generic relationship",
            "source_types": ["*"],
            "target_types": ["*"],
            "directionality": "DIRECTED",
            "is_builtin": True,
            "properties": [],
            "extraction_prompt": "",
        },
        {
            "name": "OWNS",
            "description": "Ownership relationship",
            "source_types": ["PERSON", "ORG"],
            "target_types": ["ASSET"],
            "directionality": "DIRECTED",
            "is_builtin": False,
            "properties": ["since"],
            "extraction_prompt": "Extract ownership relationships...",
        },
    ])
    store.count_relation_instances = AsyncMock(return_value=5)
    store.get_relation_type_by_name = AsyncMock(return_value={
        "name": "OWNS",
        "description": "Ownership relationship",
        "source_types": ["PERSON", "ORG"],
        "target_types": ["ASSET"],
        "directionality": "DIRECTED",
        "is_builtin": False,
        "properties": ["since"],
        "extraction_prompt": "Extract ownership relationships...",
    })
    store.create_relation_type = AsyncMock(return_value={
        "name": "USES",
        "description": "Usage relationship",
        "source_types": ["PERSON"],
        "target_types": ["TECHNOLOGY"],
        "directionality": "DIRECTED",
        "is_builtin": False,
        "properties": ["duration"],
        "extraction_prompt": "Extract usage relationships...",
    })
    store.update_relation_type = AsyncMock(return_value={
        "name": "OWNS",
        "description": "Updated ownership",
        "source_types": ["PERSON", "ORG"],
        "target_types": ["ASSET"],
        "directionality": "DIRECTED",
        "is_builtin": False,
        "properties": ["since", "percentage"],
        "extraction_prompt": "Updated extraction prompt...",
    })
    store.delete_relation_type = AsyncMock(return_value=None)

    # Ontology versions
    store.get_ontology_versions = AsyncMock(return_value=[
        {
            "version": "v2.0",
            "created_at": "2026-03-26T01:00:00Z",
            "created_by": "user-1",
            "change_summary": "Added new entity types",
            "changes": [],
            "is_active": True,
        },
        {
            "version": "v1.0",
            "created_at": "2026-03-26T00:00:00Z",
            "created_by": "system",
            "change_summary": "Initial version",
            "changes": [],
            "is_active": False,
        },
    ])
    store.get_ontology_version = AsyncMock(return_value={
        "version": "v2.0",
        "created_at": "2026-03-26T01:00:00Z",
        "created_by": "user-1",
        "change_summary": "Added new entity types",
        "changes": [],
        "is_active": True,
    })
    store.create_ontology_version = AsyncMock(return_value={
        "version": "v3.0",
        "created_at": "2026-03-26T02:00:00Z",
        "created_by": "user-2",
        "change_summary": "Major update",
        "changes": [],
        "is_active": False,
    })
    store.get_ontology_version_diff = AsyncMock(return_value={
        "added_entity_types": ["NewType1", "NewType2"],
        "removed_entity_types": ["OldType"],
        "modified_entity_types": ["ModifiedType"],
        "added_relation_types": ["NewRelation"],
        "removed_relation_types": ["OldRelation"],
        "modified_relation_types": ["ModifiedRelation"],
    })
    store.rollback_ontology_to_version = AsyncMock(return_value=True)

    return store


class TestEntityTypeManagement:
    """Test entity type CRUD operations."""

    def test_list_entity_types(self, client, mock_graph_store):
        """Test listing all entity types."""
        response = client.get("/api/v1/ontology/entity-types")

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert "name" in data[0]
        assert "is_builtin" in data[0]
        assert "instance_count" in data[0]

    def test_list_entity_types_exclude_builtin(self, client, mock_graph_store):
        """Test listing entity types excluding built-in ones."""
        response = client.get("/api/v1/ontology/entity-types?include_builtin=false")

        assert response.status_code == 200
        mock_graph_store.get_entity_types.assert_called_once_with(include_builtin=False)

    def test_list_entity_types_without_counts(self, client, mock_graph_store):
        """Test listing entity types without instance counts."""
        response = client.get("/api/v1/ontology/entity-types?include_counts=false")

        assert response.status_code == 200
        # Should not call count_entity_instances
        mock_graph_store.count_entity_instances.assert_not_called()

    def test_create_entity_type_success(self, client, mock_graph_store):
        """Test creating a new custom entity type."""
        entity_type_data = {
        "name": "NewEntity",
        "description": "A new entity",
        "color": "#ff7b72",
        "icon": "plus",
        "extraction_prompt_template": "Extract new entities...",
        }

        response = client.post(
            "/api/v1/ontology/entity-types",
            json=entity_type_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "NewEntity"
        assert not data["is_builtin"]
        assert data["instance_count"] == 0
        mock_graph_store.create_entity_type.assert_called_once()

    def test_create_entity_type_conflict(self, client, mock_graph_store):
        """Test creating an entity type that already exists."""
        mock_graph_store.get_entity_type_by_name = AsyncMock(return_value={
        "name": "ExistingType",
        "is_builtin": False,
        })

        response = client.post(
            "/api/v1/ontology/entity-types",
            json={"name": "ExistingType", "description": "Existing"},
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_update_entity_type_success(self, client, mock_graph_store):
        """Test updating an existing entity type."""
        update_data = {
        "description": "Updated description",
        "color": "#7ee787",
        "icon": "tag",
        "extraction_prompt_template": "Updated template...",
        }

        response = client.put(
            "/api/v1/ontology/entity-types/CustomEntity",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"
        assert data["extraction_prompt_template"] == "Updated template..."
        mock_graph_store.update_entity_type.assert_called_once()

    def test_update_entity_type_not_found(self, client, mock_graph_store):
        """Test updating a non-existent entity type."""
        mock_graph_store.get_entity_type_by_name = AsyncMock(return_value=None)

        response = client.put(
            "/api/v1/ontology/entity-types/NonExistent",
            json={"description": "Updated"},
        )

        assert response.status_code == 404

    def test_update_entity_type_builtin_forbidden(self, client, mock_graph_store):
        """Test that built-in entity types cannot be modified."""
        mock_graph_store.get_entity_type_by_name = AsyncMock(return_value={
        "name": "PERSON",
        "is_builtin": True,
        })

        response = client.put(
            "/api/v1/ontology/entity-types/PERSON",
            json={"description": "Updated"},
        )

        assert response.status_code == 403
        assert "Cannot modify built-in" in response.json()["detail"]

    def test_delete_entity_type_success(self, client, mock_graph_store):
        """Test deleting a custom entity type."""
        mock_graph_store.count_entity_instances = AsyncMock(return_value=0)

        response = client.delete("/api/v1/ontology/entity-types/CustomEntity")

        assert response.status_code == 204
        mock_graph_store.delete_entity_type.assert_called_once_with("CustomEntity")

    def test_delete_entity_type_not_found(self, client, mock_graph_store):
        """Test deleting a non-existent entity type."""
        mock_graph_store.get_entity_type_by_name = AsyncMock(return_value=None)

        response = client.delete("/api/v1/ontology/entity-types/NonExistent")

        assert response.status_code == 404

    def test_delete_entity_type_builtin_forbidden(self, client, mock_graph_store):
        """Test that built-in entity types cannot be deleted."""
        mock_graph_store.get_entity_type_by_name = AsyncMock(return_value={
        "name": "PERSON",
        "is_builtin": True,
        })

        response = client.delete("/api/v1/ontology/entity-types/PERSON")

        assert response.status_code == 403
        assert "Cannot delete built-in" in response.json()["detail"]

    def test_delete_entity_type_with_instances(self, client, mock_graph_store):
        """Test that entity types with instances cannot be deleted."""
        mock_graph_store.count_entity_instances = AsyncMock(return_value=5)

        response = client.delete("/api/v1/ontology/entity-types/CustomEntity")

        assert response.status_code == 409
        assert "Cannot delete" in response.json()["detail"]


class TestRelationTypeManagement:
    """Test relation type CRUD operations."""

    def test_list_relation_types(self, client, mock_graph_store):
        """Test listing all relation types."""
        response = client.get("/api/v1/ontology/relation-types")

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert "name" in data[0]
        assert "is_builtin" in data[0]
        assert "instance_count" in data[0]

    def test_create_relation_type_success(self, client, mock_graph_store):
        """Test creating a new custom relation type."""
        relation_type_data = {
        "name": "USES",
        "description": "Usage relationship",
        "source_types": ["PERSON"],
        "target_types": ["TECHNOLOGY"],
        "directionality": "DIRECTED",
        "properties": ["duration"],
        "extraction_prompt": "Extract usage relationships...",
        }

        response = client.post(
            "/api/v1/ontology/relation-types",
            json=relation_type_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "USES"
        assert not data["is_builtin"]
        assert data["instance_count"] == 0
        mock_graph_store.create_relation_type.assert_called_once()

    def test_update_relation_type_success(self, client, mock_graph_store):
        """Test updating an existing relation type."""
        update_data = {
        "description": "Updated ownership",
        "properties": ["since", "percentage"],
        "extraction_prompt": "Updated extraction prompt...",
        }

        response = client.put(
            "/api/v1/ontology/relation-types/OWNS",
            json=update_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated ownership"
        assert len(data["properties"]) == 2
        mock_graph_store.update_relation_type.assert_called_once()

    def test_delete_relation_type_success(self, client, mock_graph_store):
        """Test deleting a custom relation type."""
        mock_graph_store.count_relation_instances = AsyncMock(return_value=0)

        response = client.delete("/api/v1/ontology/relation-types/OWNS")

        assert response.status_code == 204
        mock_graph_store.delete_relation_type.assert_called_once_with("OWNS")


class TestOntologyVersioning:
    """Test ontology versioning operations."""

    def test_list_ontology_versions(self, client, mock_graph_store):
        """Test listing ontology version history."""
        response = client.get("/api/v1/ontology/versions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert "version" in data[0]
        assert "created_at" in data[0]
        assert "created_by" in data[0]
        assert "change_summary" in data[0]

    def test_list_ontology_versions_limit(self, client, mock_graph_store):
        """Test listing ontology versions with custom limit."""
        response = client.get("/api/v1/ontology/versions?limit=5")

        assert response.status_code == 200
        mock_graph_store.get_ontology_versions.assert_called_once_with(limit=5)

    def test_create_ontology_version_success(self, client, mock_graph_store):
        """Test creating a new ontology version."""
        version_data = {
        "version": "v3.0",
        "change_summary": "Major update",
        "changes": [
            {"type": "added", "entity_type": "NewEntity"},
        ],
        "created_by": "test-user",
        }

        response = client.post(
            "/api/v1/ontology/versions",
            json=version_data,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["version"] == "v3.0"
        assert data["change_summary"] == "Major update"
        mock_graph_store.create_ontology_version.assert_called_once()

    def test_create_ontology_version_conflict(self, client, mock_graph_store):
        """Test creating an ontology version that already exists."""
        mock_graph_store.get_ontology_version = AsyncMock(return_value={
        "version": "v2.0",
        "is_active": True,
        })

        response = client.post(
            "/api/v1/ontology/versions",
            json={"version": "v2.0", "change_summary": "Update"},
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_get_ontology_diff(self, client, mock_graph_store):
        """Test getting diff between ontology versions."""
        response = client.get("/api/v1/ontology/versions/v2.0/diff")

        assert response.status_code == 200
        data = response.json()
        assert "added_entity_types" in data
        assert "removed_entity_types" in data
        assert "modified_entity_types" in data
        assert "added_relation_types" in data
        assert "removed_relation_types" in data
        assert "modified_relation_types" in data

    def test_get_ontology_diff_with_comparison(self, client, mock_graph_store):
        """Test getting diff between two specific versions."""
        response = client.get("/api/v1/ontology/versions/v2.0/diff?compare_to=v1.0")

        assert response.status_code == 200
        mock_graph_store.get_ontology_version_diff.assert_called_once_with(
            "v2.0",
            compare_to="v1.0",
        )

    def test_rollback_ontology_version(self, client, mock_graph_store):
        """Test rolling back ontology to a previous version."""
        response = client.post("/api/v1/ontology/versions/v1.0/rollback")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["version"] == "v1.0"
        mock_graph_store.rollback_ontology_to_version.assert_called_once_with("v1.0")

    def test_rollback_ontology_version_not_found(self, client, mock_graph_store):
        """Test rolling back to a non-existent version."""
        mock_graph_store.get_ontology_version = AsyncMock(return_value=None)

        response = client.post("/api/v1/ontology/versions/nonexistent/rollback")

        assert response.status_code == 404


class TestAuditIntegration:
    """Test audit logging integration."""

    def test_audit_logged_on_create(self, client, mock_graph_store):
        """Test that audit events are logged on entity type creation."""
        with patch("app.api.routes.ontology.AuditLogger") as mock_audit:
            response = client.post(
                "/api/v1/ontology/entity-types",
                json={"name": "NewEntity", "description": "New entity"},
            )

            assert response.status_code == 201
            assert mock_audit.called
            # Audit logger should have been instantiated
            assert mock_audit.return_value.log_event.called

    def test_audit_logged_on_update(self, client, mock_graph_store):
        """Test that audit events are logged on entity type update."""
        with patch("app.api.routes.ontology.AuditLogger") as mock_audit:
            response = client.put(
                "/api/v1/ontology/entity-types/CustomEntity",
                json={"description": "Updated"},
            )

            assert response.status_code == 200
            assert mock_audit.called

    def test_audit_logged_on_delete(self, client, mock_graph_store):
        """Test that audit events are logged on entity type deletion."""
        mock_graph_store.count_entity_instances = AsyncMock(return_value=0)

        with patch("app.api.routes.ontology.AuditLogger") as mock_audit:
            response = client.delete("/api/v1/ontology/entity-types/CustomEntity")

            assert response.status_code == 204
            assert mock_audit.called
