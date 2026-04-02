"""Domain management API routes.

Provides endpoints for:
- Domain CRUD operations
- Domain activation and context switching
- Domain namespace isolation
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import GraphStoreDep
from app.config import get_settings
from app.api.schemas.domains import (
    DomainActivateResponse,
    DomainCreateSchema,
    DomainInheritanceChainSchema,
    DomainSchema,
    DomainUpdateSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/domains", tags=["Domain Management"])


def _domain_to_schema(domain_dict: dict[str, Any]) -> DomainSchema:
    """Convert domain dict to DomainSchema."""
    return DomainSchema(
        id=domain_dict["id"],
        name=domain_dict["name"],
        description=domain_dict.get("description", ""),
        domain_key=domain_dict["domain_key"],
        metadata={
            "created_at": datetime.fromisoformat(domain_dict["created_at"].replace("Z", "+00:00"))
            if isinstance(domain_dict["created_at"], str)
            else domain_dict["created_at"],
            "updated_at": datetime.fromisoformat(domain_dict["updated_at"].replace("Z", "+00:00"))
            if isinstance(domain_dict["updated_at"], str)
            else domain_dict["updated_at"],
            "created_by": domain_dict.get("created_by", "system"),
            "version": domain_dict.get("version", "1.0.0"),
            "is_active": domain_dict.get("is_active", False),
        },
        config={
            "parent_domain_key": domain_dict.get("parent_domain_key"),
            "inherits_base_ontology": domain_dict.get("inherits_base_ontology", True),
        },
    )


@router.get(
    "",
    response_model=list[DomainSchema],
    summary="List domains",
    description="Get all domains (active by default).",
)
async def list_domains(
    store: GraphStoreDep,
    include_inactive: bool = Query(default=False, description="Include inactive domains"),
) -> list[DomainSchema]:
    """List all domains."""
    try:
        domains = await store.list_domains(include_inactive=include_inactive)
        return [_domain_to_schema(d) for d in domains]
    except Exception as exc:
        logger.exception("Failed to list domains: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list domains: {exc}",
        ) from exc


@router.post(
    "",
    response_model=DomainSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create domain",
)
async def create_domain(
    domain: DomainCreateSchema,
    store: GraphStoreDep,
) -> DomainSchema:
    """Create a new domain."""
    try:
        existing = await store.get_domain_by_key(domain.domain_key)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Domain {domain.domain_key} already exists",
            )

        created = await store.create_domain(
            domain_key=domain.domain_key,
            name=domain.name,
            description=domain.description,
            parent_domain_key=domain.parent_domain_key,
            inherits_base_ontology=domain.inherits_base_ontology,
        )

        return _domain_to_schema(created)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create domain: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create domain: {exc}",
        ) from exc


@router.get(
    "/active",
    response_model=DomainSchema,
    summary="Get active domain",
)
async def get_active_domain(store: GraphStoreDep) -> DomainSchema:
    """Get the currently active domain.

    Registered before ``/{domain_key}`` so ``active`` is not captured as a domain key.
    When ``domain_auto_bootstrap`` is enabled (default), creates or activates a default
    domain so this endpoint does not return 404 on an empty graph.
    """
    try:
        settings = get_settings()
        if settings.app.domain_auto_bootstrap:
            domain = await store.ensure_default_active_domain(
                default_domain_key=settings.app.default_domain_key,
                default_name=settings.app.default_domain_name,
            )
        else:
            domain = await store.get_active_domain()
        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active domain found",
            )
        return _domain_to_schema(domain)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get active domain: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active domain: {exc}",
        ) from exc


@router.get(
    "/{domain_key}",
    response_model=DomainSchema,
    summary="Get domain",
)
async def get_domain(
    domain_key: str,
    store: GraphStoreDep,
) -> DomainSchema:
    """Get domain details by key."""
    try:
        domain = await store.get_domain_by_key(domain_key)
        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain {domain_key} not found",
            )
        return _domain_to_schema(domain)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get domain: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get domain: {exc}",
        ) from exc


@router.put(
    "/{domain_key}",
    response_model=DomainSchema,
    summary="Update domain",
)
async def update_domain(
    domain_key: str,
    domain: DomainUpdateSchema,
    store: GraphStoreDep,
) -> DomainSchema:
    """Update a domain."""
    try:
        existing = await store.get_domain_by_key(domain_key)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain {domain_key} not found",
            )

        update_data: dict[str, Any] = {}
        if domain.name is not None:
            update_data["name"] = domain.name
        if domain.description is not None:
            update_data["description"] = domain.description
        if domain.extraction_prompt_template is not None:
            update_data["extraction_prompt_template"] = domain.extraction_prompt_template
        if domain.parent_domain_key is not None:
            update_data["parent_domain_key"] = domain.parent_domain_key
        if domain.inherits_base_ontology is not None:
            update_data["inherits_base_ontology"] = domain.inherits_base_ontology

        updated = await store.update_domain(domain_key, **update_data)
        return _domain_to_schema(updated)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update domain: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update domain: {exc}",
        ) from exc


@router.delete(
    "/{domain_key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete domain",
)
async def delete_domain(
    domain_key: str,
    store: GraphStoreDep,
) -> None:
    """Delete a domain."""
    try:
        success = await store.delete_domain(domain_key)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain {domain_key} not found",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to delete domain: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete domain: {exc}",
        ) from exc


@router.post(
    "/{domain_key}/activate",
    response_model=DomainActivateResponse,
    summary="Activate domain",
)
async def activate_domain(
    domain_key: str,
    store: GraphStoreDep,
) -> DomainActivateResponse:
    """Activate a domain and set it as the current context."""
    try:
        domain = await store.get_domain_by_key(domain_key)
        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain {domain_key} not found",
            )

        success = await store.activate_domain(domain_key)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to activate domain {domain_key}",
            )

        return DomainActivateResponse(
            success=True,
            message=f"Domain {domain_key} activated successfully",
            domain_key=domain_key,
            activated_at=datetime.utcnow(),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to activate domain: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate domain: {exc}",
        ) from exc


@router.get(
    "/{domain_key}/entity-types",
    response_model=list[Any],
    summary="Get domain entity types",
)
async def get_domain_entity_types(
    domain_key: str,
    store: GraphStoreDep,
) -> list[Any]:
    """Get entity types belonging to a domain."""
    try:
        domain = await store.get_domain_by_key(domain_key)
        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain {domain_key} not found",
            )

        entity_types = await store.get_domain_entity_types(domain_key)
        return entity_types
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get domain entity types: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get domain entity types: {exc}",
        ) from exc


@router.get(
    "/{domain_key}/relation-types",
    response_model=list[Any],
    summary="Get domain relation types",
)
async def get_domain_relation_types(
    domain_key: str,
    store: GraphStoreDep,
) -> list[Any]:
    """Get relation types belonging to a domain."""
    try:
        domain = await store.get_domain_by_key(domain_key)
        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain {domain_key} not found",
            )

        relation_types = await store.get_domain_relation_types(domain_key)
        return relation_types
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get domain relation types: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get domain relation types: {exc}",
        ) from exc


@router.get(
    "/{domain_key}/inheritance-chain",
    response_model=list[DomainInheritanceChainSchema],
    summary="Get domain inheritance chain",
)
async def get_domain_inheritance_chain(
    domain_key: str,
    store: GraphStoreDep,
) -> list[DomainInheritanceChainSchema]:
    """Get the inheritance chain for a domain."""
    try:
        domain = await store.get_domain_by_key(domain_key)
        if not domain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Domain {domain_key} not found",
            )

        chain = await store.get_domain_inheritance_chain(domain_key)
        return [
            DomainInheritanceChainSchema(
                domain_key=d["domain_key"],
                name=d["name"],
                inherits_from=d.get("parent_domain_key"),
            )
            for d in chain
        ]
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get domain inheritance chain: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get domain inheritance chain: {exc}",
        ) from exc
