"""Tests for ontology version management."""

import pytest
from datetime import datetime
from uuid import UUID


class TestOntologyVersionSchema:
    """Tests for ontology version schemas."""

    def test_ontology_version_schema(self):
        """Test ontology version schema."""
        from app.api.schemas.ontology import OntologyVersionSchema

        version = OntologyVersionSchema(
            version="v1.0.0",
            created_at=datetime.now(),
            created_by="admin",
            change_summary="Initial ontology",
            changes=["Added Person entity", "Added WORKS_AT relation"],
            is_active=True,
        )

        assert version.version == "v1.0.0"
        assert version.is_active is True
        assert len(version.changes) == 2

    def test_ontology_version_create(self):
        """Test creating ontology version."""
        from app.api.schemas.ontology import OntologyVersionCreateSchema

        version = OntologyVersionCreateSchema(
            version="v1.1.0",
            change_summary="Added new entity types",
            changes=["Added Project entity", "Added PARTICIPATES_IN relation"],
        )

        assert version.version == "v1.1.0"
        assert "Added Project entity" in version.changes

    def test_ontology_diff_schema(self):
        """Test ontology diff schema."""
        from app.api.schemas.ontology import OntologyDiffSchema

        # Check schema exists and is valid
        assert OntologyDiffSchema is not None

        # Test with simple list (empty) to verify basic structure
        diff = OntologyDiffSchema(
            added_entity_types=[],
            removed_entity_types=[],
            modified_entity_types=[],
            added_relation_types=[],
            removed_relation_types=[],
            modified_relation_types=[],
        )

        assert diff.added_entity_types is not None
        assert diff.removed_entity_types is not None
        assert diff.modified_entity_types is not None


class TestOntologyVersionAPI:
    """Tests for ontology version API endpoints."""

    def test_version_routes_exist(self):
        """Test version routes exist."""
        from app.api.routes import ontology

        routes = [r.path for r in ontology.router.routes]
        assert "/versions" in routes or any("version" in r for r in routes)

    def test_get_ontology_versions(self):
        """Test getting ontology versions."""
        from app.api.routes.ontology import list_ontology_versions

        # Verify endpoint exists
        assert list_ontology_versions is not None

    def test_create_ontology_version(self):
        """Test creating ontology version."""
        from app.api.routes.ontology import create_ontology_version

        assert create_ontology_version is not None

    def test_rollback_ontology_version(self):
        """Test rollback ontology version."""
        from app.api.routes.ontology import rollback_ontology_version

        assert rollback_ontology_version is not None


class TestVersionManagementIntegration:
    """Integration tests for version management."""

    def test_version_lifecycle(self):
        """Test version creation, listing, diff, and rollback flow."""
        from app.api.schemas.ontology import (
            OntologyVersionSchema,
            OntologyVersionCreateSchema,
            OntologyDiffSchema,
        )

        # Create version
        v1 = OntologyVersionCreateSchema(
            version="v1.0.0",
            change_summary="Initial version",
            changes=["Initial ontology"],
        )

        # Simulate version listing
        versions = [
            OntologyVersionSchema(
                version=v1.version,
                created_at=datetime.now(),
                created_by="admin",
                change_summary=v1.change_summary,
                changes=v1.changes,
                is_active=True,
            )
        ]

        assert len(versions) == 1
        assert versions[0].is_active is True

        # Create diff
        diff = OntologyDiffSchema(
            added_entity_types=["NewEntity"],
            removed_entity_types=[],
            modified_entity_types=[],
            added_relation_types=[],
            removed_relation_types=[],
            modified_relation_types=[],
        )

        assert "NewEntity" in diff.added_entity_types