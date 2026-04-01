"""Role-based access control."""

from enum import Enum
from functools import wraps
from typing import Callable

from fastapi import HTTPException, status


class Role(str, Enum):
    """User roles."""
    ADMIN = "admin"
    REVIEWER = "reviewer"
    USER = "user"


# Permission matrix
ROLE_PERMISSIONS = {
    Role.ADMIN: {
        "assets:read",
        "assets:write",
        "ontology:read",
        "ontology:write",
        "ontology:delete",
        "review:read",
        "review:write",
        "exploration:read",
        "exploration:write",
        "evaluation:read",
        "evaluation:write",
        "users:read",
        "users:write",
    },
    Role.REVIEWER: {
        "assets:read",
        "ontology:read",
        "review:read",
        "review:write",
        "exploration:read",
        "exploration:write",
        "evaluation:read",
    },
    Role.USER: {
        "assets:read",
        "exploration:read",
        "exploration:write:own",
    },
}


def has_permission(role: str, permission: str) -> bool:
    """Check if role has permission."""
    role_perms = ROLE_PERMISSIONS.get(Role(role), set())
    # Check exact permission or wildcard permission
    if permission in role_perms:
        return True
    # Check wildcard (e.g., "exploration:write:own" -> "exploration:write")
    base_perm = permission.split(":")[0] + ":write"
    return base_perm in role_perms


def require_permission(permission: str):
    """Decorator to require a specific permission."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # This will be used with FastAPI dependency injection
            # The actual check will be done in the dependency
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Define which roles can access which endpoints
ENDPOINT_PERMISSIONS = {
    # Metadata endpoints
    "GET /api/v1/metadata/assets": ["assets:read"],
    "GET /api/v1/metadata/{id}": ["assets:read"],
    "GET /api/v1/metadata/{id}/lineage": ["assets:read"],
    "GET /api/v1/metadata/{id}/annotations": ["assets:read"],
    "POST /api/v1/metadata/{id}/annotations": ["assets:write"],
    "PUT /api/v1/metadata/annotations/{id}": ["assets:write"],

    # Ontology endpoints
    "GET /api/v1/ontology/entity-types": ["ontology:read"],
    "POST /api/v1/ontology/entity-types": ["ontology:write"],
    "PUT /api/v1/ontology/entity-types/{name}": ["ontology:write"],
    "DELETE /api/v1/ontology/entity-types/{name}": ["ontology:delete"],
    "GET /api/v1/ontology/relation-types": ["ontology:read"],
    "POST /api/v1/ontology/relation-types": ["ontology:write"],
    "PUT /api/v1/ontology/relation-types/{name}": ["ontology:write"],
    "DELETE /api/v1/ontology/relation-types/{name}": ["ontology:delete"],
    "GET /api/v1/ontology/versions": ["ontology:read"],
    "POST /api/v1/ontology/versions": ["ontology:write"],
    "POST /api/v1/ontology/versions/{version}/rollback": ["ontology:write"],

    # Intelligence endpoints
    "GET /api/v1/intelligence/review-queue": ["review:read"],
    "POST /api/v1/intelligence/review-queue/{id}/vote": ["review:write"],
    "GET /api/v1/intelligence/explorations": ["exploration:read"],
    "POST /api/v1/intelligence/explorations": ["exploration:write"],

    # Evaluation endpoints
    "GET /api/v1/evaluation/metrics": ["evaluation:read"],
    "GET /api/v1/evaluation/pipeline/configs": ["evaluation:read"],
    "POST /api/v1/evaluation/pipeline/configs": ["evaluation:write"],
    "POST /api/v1/evaluation/pipeline/configs/{version}/activate": ["evaluation:write"],

    # User management (admin only)
    "GET /api/v1/auth/users": ["users:read"],
    "POST /api/v1/auth/users": ["users:write"],
    "PUT /api/v1/auth/users/{id}/role": ["users:write"],
}


def check_endpoint_permission(method: str, path: str, role: str) -> bool:
    """Check if role has permission to access endpoint."""
    # Find matching endpoint pattern
    for key, required_perms in ENDPOINT_PERMISSIONS.items():
        ep_method, ep_path = key.split(" ", 1)
        if method != ep_method:
            continue

        # Simple path matching (in production, use more sophisticated matching)
        if ep_path == path:
            return any(has_permission(role, perm) for perm in required_perms)

        # Handle path with parameters
        if "{" in ep_path:
            # Convert {param} to regex
            import re
            pattern = "^" + ep_path.replace("{", "(?P<").replace("}", ">[^/]+)") + "$"
            if re.match(pattern, path):
                return any(has_permission(role, perm) for perm in required_perms)

    # Default: allow if no specific permissions defined
    return True