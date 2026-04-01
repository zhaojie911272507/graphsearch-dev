"""Authentication module."""

from app.auth.token import token_service, TokenService
from app.auth.password import authenticate, get_user, hash_password, verify_password
from app.auth.roles import Role, has_permission, check_endpoint_permission
from app.auth.dependencies import (
    get_current_user,
    require_auth,
    require_role,
    User,
)

__all__ = [
    "token_service",
    "TokenService",
    "authenticate",
    "get_user",
    "hash_password",
    "verify_password",
    "Role",
    "has_permission",
    "check_endpoint_permission",
    "get_current_user",
    "require_auth",
    "require_role",
    "User",
]