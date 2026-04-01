"""Authentication dependencies for FastAPI."""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.auth.token import token_service
from app.auth.password import get_user, DEFAULT_USERS
from app.auth.roles import Role


class User(BaseModel):
    """Authenticated user."""
    id: str
    role: str
    name: str


class AuthDep:
    """Authentication dependency for extracting current user."""

    security_scheme = HTTPBearer(auto_error=False)

    def __init__(self):
        self.security = HTTPBearer(auto_error=False)

    async def __call__(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    ) -> Optional[User]:
        """Extract and verify user from token."""
        if not credentials:
            return None

        token = credentials.credentials
        payload = token_service.verify_token(token)

        if not payload:
            return None

        user = get_user(payload.sub)
        if not user:
            return None

        return User(
            id=payload.sub,
            role=user["role"],
            name=user["name"],
        )


# Singleton
get_current_user = AuthDep()


async def require_auth(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """Require authentication or raise 401."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def require_role(
    allowed_roles: list[str],
    user: User = Depends(require_auth),
) -> User:
    """Require specific role(s) or raise 403."""
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return user


# Type alias for dependency injection
CurrentUserDep = Optional[User]
AuthenticatedUserDep = User
AdminDep = User
ReviewerDep = User