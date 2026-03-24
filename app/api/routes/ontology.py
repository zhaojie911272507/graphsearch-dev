"""Ontology management API routes.

Provides endpoints for:
- Entity type CRUD
- Relation type CRUD
- Ontology versioning
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import GraphStoreDep
from app.api.schemas.ontology import (
    EntityTypeCreateSchema,
    EntityTypeSchema,
    EntityTypeUpdateSchema,
    OntologyDiffSchema,
    OntologyVersionCreateSchema,
    OntologyVersionSchema,
    RelationTypeCreateSchema,
    RelationTypeSchema,
    RelationTypeUpdateSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ontology", tags=["Ontology Management"])


@router.get(
    "/entity-types",
    response_model=list[EntityTypeSchema],
    summary="List entity types",
    description="Get all entity types (built-in and custom).",
)
async def list_entity_types(
    store: GraphStoreDep,
    include_builtin: bool = Query(default=True, description="Include built-in types"),
    include_counts: bool = Query(default=True, description="Include instance counts"),
) -> list[EntityTypeSchema]:
    """List all entity types."""
    try:
        types = await store.get_entity_types(include_builtin=include_builtin)

        result = []
        for t in types:
            instance_count = 0
            if include_counts and t.get("name"):
                instance_count = await store.count_entity_instances(t["name"])

            result.append(EntityTypeSchema(
                name=t.get("name", ""),
                description=t.get("description", ""),
                color=t.get("color", "#58a6ff"),
                icon=t.get("icon", "circle"),
                is_builtin=t.get("is_builtin", False),
                instance_count=instance_count,
                extraction_prompt_template=t.get("extraction_prompt_template", ""),
                created_at=datetime.fromisoformat(t["created_at"].replace("Z", "+00:00")) if t.get("created_at") and isinstance(t["created_at"], str) else None,
                updated_at=datetime.fromisoformat(t["updated_at"].replace("Z", "+00:00")) if t.get("updated_at") and isinstance(t["updated_at"], str) else None,
            ))

        return result
    except Exception as exc:
        logger.exception("Failed to list entity types: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list entity types: {exc}",
        ) from exc


@router.post(
    "/entity-types",
    response_model=EntityTypeSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create entity type",
)
async def create_entity_type(
    entity_type: EntityTypeCreateSchema,
    store: GraphStoreDep,
) -> EntityTypeSchema:
    """Create a new custom entity type."""
    try:
        existing = await store.get_entity_type_by_name(entity_type.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Entity type {entity_type.name} already exists",
            )

        created = await store.create_entity_type(
            name=entity_type.name,
            description=entity_type.description,
            color=entity_type.color,
            icon=entity_type.icon,
            extraction_prompt_template=entity_type.extraction_prompt_template,
        )

        return EntityTypeSchema(
            name=created["name"],
            description=created["description"],
            color=created["color"],
            icon=created["icon"],
            is_builtin=False,
            instance_count=0,
            extraction_prompt_template=created.get("extraction_prompt_template", ""),
            created_at=datetime.fromisoformat(created["created_at"].replace("Z", "+00:00")) if isinstance(created["created_at"], str) else datetime.utcnow(),
            updated_at=datetime.fromisoformat(created["updated_at"].replace("Z", "+00:00")) if isinstance(created["updated_at"], str) else datetime.utcnow(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create entity type: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create entity type: {exc}",
        ) from exc


@router.put(
    "/entity-types/{type_name}",
    response_model=EntityTypeSchema,
    summary="Update entity type",
)
async def update_entity_type(
    type_name: str,
    entity_type: EntityTypeUpdateSchema,
    store: GraphStoreDep,
) -> EntityTypeSchema:
    """Update an entity type."""
    try:
        existing = await store.get_entity_type_by_name(type_name)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity type {type_name} not found",
            )
        if existing.get("is_builtin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify built-in entity types",
            )

        update_data = {}
        if entity_type.description is not None:
            update_data["description"] = entity_type.description
        if entity_type.color is not None:
            update_data["color"] = entity_type.color
        if entity_type.icon is not None:
            update_data["icon"] = entity_type.icon
        if entity_type.extraction_prompt_template is not None:
            update_data["extraction_prompt_template"] = entity_type.extraction_prompt_template

        updated = await store.update_entity_type(type_name, **update_data)

        instance_count = await store.count_entity_instances(type_name)

        return EntityTypeSchema(
            name=updated["name"],
            description=updated["description"],
            color=updated["color"],
            icon=updated["icon"],
            is_builtin=False,
            instance_count=instance_count,
            extraction_prompt_template=updated.get("extraction_prompt_template", ""),
            created_at=datetime.fromisoformat(updated["created_at"].replace("Z", "+00:00")) if isinstance(updated["created_at"], str) else datetime.utcnow(),
            updated_at=datetime.fromisoformat(updated["updated_at"].replace("Z", "+00:00")) if isinstance(updated["updated_at"], str) else datetime.utcnow(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update entity type: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update entity type: {exc}",
        ) from exc


@router.delete(
    "/entity-types/{type_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete entity type",
)
async def delete_entity_type(
    type_name: str,
    store: GraphStoreDep,
) -> None:
    """Delete a custom entity type."""
    try:
        existing = await store.get_entity_type_by_name(type_name)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity type {type_name} not found",
            )
        if existing.get("is_builtin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete built-in entity types",
            )

        instance_count = await store.count_entity_instances(type_name)
        if instance_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete entity type with {instance_count} instances",
            )

        await store.delete_entity_type(type_name)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to delete entity type: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete entity type: {exc}",
        ) from exc


@router.get(
    "/relation-types",
    response_model=list[RelationTypeSchema],
    summary="List relation types",
)
async def list_relation_types(
    store: GraphStoreDep,
    include_builtin: bool = Query(default=True, description="Include built-in relations"),
    include_counts: bool = Query(default=True, description="Include instance counts"),
) -> list[RelationTypeSchema]:
    """List all relation types."""
    try:
        types = await store.get_relation_types(include_builtin=include_builtin)

        result = []
        for t in types:
            instance_count = 0
            if include_counts and t.get("name"):
                instance_count = await store.count_relation_instances(t["name"])

            result.append(RelationTypeSchema(
                name=t.get("name", ""),
                description=t.get("description", ""),
                source_types=t.get("source_types", []),
                target_types=t.get("target_types", []),
                directionality=t.get("directionality", "DIRECTED"),
                is_builtin=t.get("is_builtin", False),
                instance_count=instance_count,
                properties=t.get("properties", []),
                extraction_prompt=t.get("extraction_prompt", ""),
            ))

        return result
    except Exception as exc:
        logger.exception("Failed to list relation types: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list relation types: {exc}",
        ) from exc


@router.post(
    "/relation-types",
    response_model=RelationTypeSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create relation type",
)
async def create_relation_type(
    relation_type: RelationTypeCreateSchema,
    store: GraphStoreDep,
) -> RelationTypeSchema:
    """Create a new custom relation type."""
    try:
        existing = await store.get_relation_type_by_name(relation_type.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Relation type {relation_type.name} already exists",
            )

        created = await store.create_relation_type(
            name=relation_type.name,
            description=relation_type.description,
            source_types=relation_type.source_types,
            target_types=relation_type.target_types,
            directionality=relation_type.directionality,
            properties=relation_type.properties,
            extraction_prompt=relation_type.extraction_prompt,
        )

        return RelationTypeSchema(
            name=created["name"],
            description=created["description"],
            source_types=created.get("source_types", []),
            target_types=created.get("target_types", []),
            directionality=created.get("directionality", "DIRECTED"),
            is_builtin=False,
            instance_count=0,
            properties=created.get("properties", []),
            extraction_prompt=created.get("extraction_prompt", ""),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create relation type: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create relation type: {exc}",
        ) from exc


@router.put(
    "/relation-types/{type_name}",
    response_model=RelationTypeSchema,
    summary="Update relation type",
)
async def update_relation_type(
    type_name: str,
    relation_type: RelationTypeUpdateSchema,
    store: GraphStoreDep,
) -> RelationTypeSchema:
    """Update a relation type."""
    try:
        existing = await store.get_relation_type_by_name(type_name)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Relation type {type_name} not found",
            )
        if existing.get("is_builtin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify built-in relation types",
            )

        update_data = {}
        if relation_type.description is not None:
            update_data["description"] = relation_type.description
        if relation_type.source_types is not None:
            update_data["source_types"] = relation_type.source_types
        if relation_type.target_types is not None:
            update_data["target_types"] = relation_type.target_types
        if relation_type.directionality is not None:
            update_data["directionality"] = relation_type.directionality
        if relation_type.properties is not None:
            update_data["properties"] = relation_type.properties
        if relation_type.extraction_prompt is not None:
            update_data["extraction_prompt"] = relation_type.extraction_prompt

        updated = await store.update_relation_type(type_name, **update_data)

        instance_count = await store.count_relation_instances(type_name)

        return RelationTypeSchema(
            name=updated["name"],
            description=updated["description"],
            source_types=updated.get("source_types", []),
            target_types=updated.get("target_types", []),
            directionality=updated.get("directionality", "DIRECTED"),
            is_builtin=False,
            instance_count=instance_count,
            properties=updated.get("properties", []),
            extraction_prompt=updated.get("extraction_prompt", ""),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update relation type: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update relation type: {exc}",
        ) from exc


@router.delete(
    "/relation-types/{type_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete relation type",
)
async def delete_relation_type(
    type_name: str,
    store: GraphStoreDep,
) -> None:
    """Delete a custom relation type."""
    try:
        existing = await store.get_relation_type_by_name(type_name)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Relation type {type_name} not found",
            )
        if existing.get("is_builtin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete built-in relation types",
            )

        instance_count = await store.count_relation_instances(type_name)
        if instance_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot delete relation type with {instance_count} instances",
            )

        await store.delete_relation_type(type_name)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to delete relation type: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete relation type: {exc}",
        ) from exc


@router.get(
    "/versions",
    response_model=list[OntologyVersionSchema],
    summary="List ontology versions",
)
async def list_ontology_versions(
    store: GraphStoreDep,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[OntologyVersionSchema]:
    """List ontology version history."""
    try:
        versions = await store.get_ontology_versions(limit=limit)

        return [
            OntologyVersionSchema(
                version=v["version"],
                created_at=datetime.fromisoformat(v["created_at"].replace("Z", "+00:00")) if isinstance(v["created_at"], str) else v["created_at"],
                created_by=v["created_by"],
                change_summary=v["change_summary"],
                changes=v.get("changes", []),
                is_active=v.get("is_active", False),
            )
            for v in versions
        ]
    except Exception as exc:
        logger.exception("Failed to list ontology versions: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list ontology versions: {exc}",
        ) from exc


@router.post(
    "/versions",
    response_model=OntologyVersionSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create ontology version",
)
async def create_ontology_version(
    version: OntologyVersionCreateSchema,
    store: GraphStoreDep,
) -> OntologyVersionSchema:
    """Create a new ontology version (snapshot)."""
    try:
        existing = await store.get_ontology_version(version.version)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Version {version.version} already exists",
            )

        created = await store.create_ontology_version(
            version=version.version,
            change_summary=version.change_summary,
            changes=version.changes,
            created_by="current_user",
        )

        return OntologyVersionSchema(
            version=created["version"],
            created_at=datetime.fromisoformat(created["created_at"].replace("Z", "+00:00")) if isinstance(created["created_at"], str) else datetime.utcnow(),
            created_by=created["created_by"],
            change_summary=created["change_summary"],
            changes=created.get("changes", []),
            is_active=created.get("is_active", True),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create ontology version: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ontology version: {exc}",
        ) from exc


@router.get(
    "/versions/{version}/diff",
    response_model=OntologyDiffSchema,
    summary="Get ontology diff",
)
async def get_ontology_diff(
    version: str,
    store: GraphStoreDep,
    compare_to: str | None = Query(default=None, description="Compare to version (default: previous)"),
) -> OntologyDiffSchema:
    """Get diff between ontology versions."""
    try:
        diff = await store.get_ontology_version_diff(version, compare_to=compare_to)

        return OntologyDiffSchema(
            added_entity_types=diff.get("added_entity_types", []),
            removed_entity_types=diff.get("removed_entity_types", []),
            modified_entity_types=diff.get("modified_entity_types", []),
            added_relation_types=diff.get("added_relation_types", []),
            removed_relation_types=diff.get("removed_relation_types", []),
            modified_relation_types=diff.get("modified_relation_types", []),
        )
    except Exception as exc:
        logger.exception("Failed to get ontology diff: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ontology diff: {exc}",
        ) from exc


@router.post(
    "/versions/{version}/rollback",
    summary="Rollback to ontology version",
)
async def rollback_ontology_version(
    version: str,
    store: GraphStoreDep,
) -> dict:
    """Rollback ontology to a previous version."""
    try:
        target = await store.get_ontology_version(version)
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Version {version} not found",
            )

        result = await store.rollback_ontology_to_version(version)

        return {
            "success": result,
            "message": f"Rolled back to version {version}",
            "version": version,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to rollback ontology: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rollback ontology: {exc}",
        ) from exc
