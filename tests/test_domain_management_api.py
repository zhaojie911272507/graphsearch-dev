"""Tests for domain management API endpoints.

Covers:
- Domain CRUD operations
- Domain activation and context switching
- Domain-specific ontology management
- Domain inheritance chain
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app


@pytest.fixture
def client(mock_graph_store):
    """Create FastAPI test client with mocked graph store."""
    # Set up app.state with mock
    app.state.graph_store = mock_graph_store
    return TestClient(app)


@pytest.fixture
def mock_graph_store():
    """Mock GraphStore for domain management operations."""
    store = AsyncMock()

    # List domains
    store.list_domains = AsyncMock(return_value=[
        {
            "id": str(uuid4()),
            "name": "Technology",
            "description": "Technology domain",
            "domain_key": "tech",
            "domain_key": "tech",
            "created_at": "2026-03-26T00:00:00Z",
            "updated_at": "2026-03-26T00:00:00Z",
            "created_by": "system",
            "version": "1.0.0",
            "is_active": True,
            "extraction_prompt_template": "Extract technology entities...",
            "max_entity_types": 50,
            "max_relation_types": 100,
            "validation_rules": {},
            "parent_domain_key": None,
            "inherits_base_ontology": True,
            "entity_types": [],
            "relation_types": [],
        }
    ])

    # Get domain by key
    store.get_domain_by_key = AsyncMock(return_value={
        "id": str(uuid4()),
        "name": "Healthcare",
        "description": "Healthcare domain",
        "domain_key": "healthcare",
        "created_at": "2026-03-26T00:00:00Z",
        "updated_at": "2026-03-26T00:00:00Z",
        "created_by": "system",
        "version": "1.0.0",
        "is_active": False,
        "extraction_prompt_template": "Extract healthcare entities...",
        "max_entity_types": 50,
        "max_relation_types": 100,
        "validation_rules": {},
        "parent_domain_key": None,
        "inherits_base_ontology": True,
        "entity_types": [],
        "relation_types": [],
    })

    # Create domain
    store.create_domain = AsyncMock(return_value={
        "id": str(uuid4()),
        "name": "Finance",
        "description": "Finance domain",
        "domain_key": "finance",
        "created_at": "2026-03-26T00:00:00Z",
        "updated_at": "2026-03-26T00:00:00Z",
        "created_by": "test-user",
        "version": "1.0.0",
        "is_active": False,
        "extraction_prompt_template": "Extract financial entities...",
        "max_entity_types": 50,
        "max_relation_types": 100,
        "validation_rules": {},
        "parent_domain_key": None,
        "inherits_base_ontology": True,
        "entity_types": [],
        "relation_types": [],
    })

    # Update domain
    store.update_domain = AsyncMock(return_value={
        "id": str(uuid4()),
        "name": "Finance Updated",
        "description": "Updated finance domain",
        "domain_key": "finance",
        "created_at": "2026-03-26T00:00:00Z",
        "updated_at": "2026-03-26T01:00:00Z",
        "created_by": "test-user",
        "version": "1.0.0",
        "is_active": False,
        "extraction_prompt_template": "Updated template...",
        "max_entity_types": 50,
        "max_relation_types": 100,
        "validation_rules": {},
        "parent_domain_key": "tech",
        "inherits_base_ontology": False,
        "entity_types": [],
        "relation_types": [],
    })

    # Delete domain
    store.delete_domain = AsyncMock(return_value=True)

    # Activate domain
    store.activate_domain = AsyncMock(return_value=True)
    store.get_active_domain = AsyncMock(return_value={
        "id": str(uuid4()),
        "name": "Active Domain",
        "description": "Currently active domain",
        "domain_key": "active",
        "created_at": "2026-03-26T00:00:00Z",
        "updated_at": "2026-03-26T00:00:00Z",
        "created_by": "system",
        "version": "1.0.0",
        "is_active": True,
        "extraction_prompt_template": "Active template...",
        "max_entity_types": 50,
        "max_relation_types": 100,
        "validation_rules": {},
        "parent_domain_key": None,
        "inherits_base_ontology": True,
        "entity_types": [],
        "relation_types": [],
    })

    # Domain entity/relation types
    store.get_domain_entity_types = AsyncMock(return_value=[])
    store.get_domain_relation_types = AsyncMock(return_value=[])

    # Inheritance chain
    store.get_domain_inheritance_chain = AsyncMock(return_value=[
        {"domain_key": "finance", "name": "Finance", "parent_domain_key": "tech"},
        {"domain_key": "tech", "name": "Technology", "parent_domain_key": None},
    ])

    return store


class TestDomainCRUD:
    """Test domain CRUD operations."""

    def test_list_domains(self, client, mock_graph_store):
        """Test listing all domains."""
        response = client.get("/api/v1/domains")

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert "name" in data[0]
        assert "domain_key" in data[0]
        assert "metadata" in data[0]
        assert "is_active" in data[0]["metadata"]

    def test_list_domains_include_inactive(self, client, mock_graph_store):
        """Test listing domains including inactive ones."""
        response = client.get("/api/v1/domains?include_inactive=true")

        assert response.status_code == 200
        mock_graph_store.list_domains.assert_called_once_with(include_inactive=True)

    def test_create_domain_success(self, client, mock_graph_store):
        """Test creating a new domain."""
        domain_data = {
            "name": "Finance",
            "domain_key": "finance",
            "description": "Finance domain",
            "extraction_prompt_template": "Extract financial entities...",
            "parent_domain_key": None,
            "inherits_base_ontology": True,
        }

        # Mock get_domain_by_key to return None (domain doesn't exist yet)
        mock_graph_store.get_domain_by_key = AsyncMock(return_value=None)
        mock_graph_store.create_domain = AsyncMock(return_value={
            "id": str(uuid4()),
            "name": "Finance",
            "description": "Finance domain",
            "domain_key": "finance",
            "created_at": "2026-03-26T00:00:00Z",
            "updated_at": "2026-03-26T00:00:00Z",
            "created_by": "system",
            "version": "1.0.0",
            "is_active": False,
            "extraction_prompt_template": "Extract financial entities...",
            "max_entity_types": 50,
            "max_relation_types": 100,
            "validation_rules": {},
            "parent_domain_key": None,
            "inherits_base_ontology": True,
            "entity_types": [],
            "relation_types": [],
        })

        response = client.post("/api/v1/domains", json=domain_data)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Finance"
        assert data["domain_key"] == "finance"
        assert not data["metadata"]["is_active"]
        mock_graph_store.create_domain.assert_called_once()

    def test_create_domain_conflict(self, client, mock_graph_store):
        """Test creating a domain that already exists."""
        mock_graph_store.get_domain_by_key = AsyncMock(return_value={
            "id": str(uuid4()),
            "name": "Existing",
            "domain_key": "existing",
        })

        response = client.post(
            "/api/v1/domains",
            json={
                "name": "Existing",
                "domain_key": "existing",
                "description": "Existing domain",
            },
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_get_domain(self, client, mock_graph_store):
        """Test getting domain details by key."""
        response = client.get("/api/v1/domains/healthcare")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Healthcare"
        assert data["domain_key"] == "healthcare"
        assert data["description"] == "Healthcare domain"

    def test_get_domain_not_found(self, client, mock_graph_store):
        """Test getting a non-existent domain."""
        mock_graph_store.get_domain_by_key = AsyncMock(return_value=None)

        response = client.get("/api/v1/domains/nonexistent")

        assert response.status_code == 404

    def test_update_domain_success(self, client, mock_graph_store):
        """Test updating a domain."""
        update_data = {
            "name": "Finance Updated",
            "description": "Updated finance domain",
            "extraction_prompt_template": "Updated template...",
            "parent_domain_key": "tech",
            "inherits_base_ontology": False,
        }

        response = client.put("/api/v1/domains/finance", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Finance Updated"
        assert data["config"]["parent_domain_key"] == "tech"
        mock_graph_store.update_domain.assert_called_once()

    def test_update_domain_not_found(self, client, mock_graph_store):
        """Test updating a non-existent domain."""
        mock_graph_store.get_domain_by_key = AsyncMock(return_value=None)

        response = client.put(
            "/api/v1/domains/nonexistent",
            json={"name": "Updated"},
        )

        assert response.status_code == 404

    def test_delete_domain(self, client, mock_graph_store):
        """Test deleting a domain."""
        response = client.delete("/api/v1/domains/finance")

        assert response.status_code == 204
        mock_graph_store.delete_domain.assert_called_once_with("finance")

    def test_delete_domain_not_found(self, client, mock_graph_store):
        """Test deleting a non-existent domain."""
        mock_graph_store.delete_domain = AsyncMock(return_value=False)

        response = client.delete("/api/v1/domains/nonexistent")

        assert response.status_code == 404


class TestDomainActivation:
    """Test domain activation and context switching."""

    def test_activate_domain_success(self, client, mock_graph_store):
        """Test activating a domain."""
        response = client.post("/api/v1/domains/finance/activate")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["domain_key"] == "finance"
        assert "activated_at" in data
        mock_graph_store.activate_domain.assert_called_once_with("finance")

    def test_activate_domain_not_found(self, client, mock_graph_store):
        """Test activating a non-existent domain."""
        mock_graph_store.get_domain_by_key = AsyncMock(return_value=None)

        response = client.post("/api/v1/domains/nonexistent/activate")

        assert response.status_code == 404

    def test_get_active_domain(self, client, mock_graph_store):
        """Test getting the currently active domain."""
        # Mock ensure_default_active_domain to return a valid domain
        mock_graph_store.ensure_default_active_domain = AsyncMock(return_value={
            "id": str(uuid4()),
            "name": "Default Domain",
            "domain_key": "default",
            "created_at": "2026-03-26T00:00:00Z",
            "updated_at": "2026-03-26T00:00:00Z",
            "created_by": "system",
            "version": "1.0.0",
            "is_active": True,
            "extraction_prompt_template": "",
            "max_entity_types": 50,
            "max_relation_types": 100,
            "validation_rules": {},
            "parent_domain_key": None,
            "inherits_base_ontology": True,
            "entity_types": [],
            "relation_types": [],
        })

        response = client.get("/api/v1/domains/active")

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"]["is_active"] is True

    def test_get_active_domain_not_found(self, client, mock_graph_store):
        """Test when no active domain exists."""
        # Mock to raise an exception
        mock_graph_store.ensure_default_active_domain = AsyncMock(side_effect=Exception("No active domain"))
        mock_graph_store.get_active_domain = AsyncMock(return_value=None)

        response = client.get("/api/v1/domains/active")

        # Should return 500 since the code tries to auto-bootstrap
        assert response.status_code == 500


class TestDomainOntology:
    """Test domain-specific ontology management."""

    def test_get_domain_entity_types(self, client, mock_graph_store):
        """Test getting entity types for a domain."""
        mock_graph_store.get_domain_entity_types = AsyncMock(return_value=[
            {
                "name": "Company",
                "description": "A business entity",
                "is_builtin": False,
            }
        ])

        response = client.get("/api/v1/domains/finance/entity-types")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_domain_entity_types_not_found(self, client, mock_graph_store):
        """Test getting entity types for non-existent domain."""
        mock_graph_store.get_domain_by_key = AsyncMock(return_value=None)

        response = client.get("/api/v1/domains/nonexistent/entity-types")

        assert response.status_code == 404

    def test_get_domain_relation_types(self, client, mock_graph_store):
        """Test getting relation types for a domain."""
        mock_graph_store.get_domain_relation_types = AsyncMock(return_value=[
            {
                "name": "OWNS",
                "description": "Ownership relationship",
                "is_builtin": False,
            }
        ])

        response = client.get("/api/v1/domains/finance/relation-types")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_domain_relation_types_not_found(self, client, mock_graph_store):
        """Test getting relation types for non-existent domain."""
        mock_graph_store.get_domain_by_key = AsyncMock(return_value=None)

        response = client.get("/api/v1/domains/nonexistent/relation-types")

        assert response.status_code == 404


class TestDomainInheritance:
    """Test domain inheritance chain."""

    def test_get_domain_inheritance_chain(self, client, mock_graph_store):
        """Test getting the inheritance chain for a domain."""
        response = client.get("/api/v1/domains/finance/inheritance-chain")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["domain_key"] == "finance"
        assert data[0]["inherits_from"] == "tech"
        assert data[1]["domain_key"] == "tech"
        assert data[1]["inherits_from"] is None

    def test_get_domain_inheritance_chain_not_found(self, client, mock_graph_store):
        """Test getting inheritance chain for non-existent domain."""
        mock_graph_store.get_domain_by_key = AsyncMock(return_value=None)

        response = client.get("/api/v1/domains/nonexistent/inheritance-chain")

        assert response.status_code == 404
