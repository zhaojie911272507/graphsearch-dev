"""Authentication API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth import authenticate, get_user, token_service, User, require_role, Role
from app.auth.password import DEFAULT_USERS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    """Login request."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response."""
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserInfo(BaseModel):
    """User info response."""
    id: str
    name: str
    role: str


class UserCreateRequest(BaseModel):
    """Create user request."""
    username: str
    password: str
    name: str
    role: str = "user"


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login",
    description="Authenticate user and get access token",
)
async def login(request: LoginRequest) -> LoginResponse:
    """Login with username and password."""
    if not authenticate(request.username, request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    user = get_user(request.username)
    token = token_service.create_access_token(request.username, user["role"])

    return LoginResponse(
        access_token=token,
        user={
            "id": request.username,
            "name": user["name"],
            "role": user["role"],
        },
    )


@router.get(
    "/me",
    response_model=UserInfo,
    summary="Get current user",
    description="Get authenticated user info",
)
async def get_me(user: User = Depends(require_role(["admin", "reviewer", "user"]))) -> UserInfo:
    """Get current user info."""
    return UserInfo(
        id=user.id,
        name=user.name,
        role=user.role,
    )


@router.get(
    "/users",
    response_model=list[UserInfo],
    summary="List users",
    description="List all users (admin only)",
)
async def list_users(
    user: User = Depends(require_role(["admin"])),
) -> list[UserInfo]:
    """List all users (admin only)."""
    return [
        UserInfo(id=username, name=data["name"], role=data["role"])
        for username, data in DEFAULT_USERS.items()
    ]


@router.post(
    "/users",
    response_model=UserInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description="Create a new user (admin only)",
)
async def create_user(
    request: UserCreateRequest,
    user: User = Depends(require_role(["admin"])),
) -> UserInfo:
    """Create a new user (admin only)."""
    if request.username in DEFAULT_USERS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists",
        )

    # In production, store in database
    DEFAULT_USERS[request.username] = {
        "password": f"plain:{request.password}",  # Simplified for demo
        "role": request.role,
        "name": request.name,
    }

    return UserInfo(
        id=request.username,
        name=request.name,
        role=request.role,
    )


@router.put(
    "/users/{username}/role",
    response_model=UserInfo,
    summary="Update user role",
    description="Update user role (admin only)",
)
async def update_user_role(
    username: str,
    role: str = Query(..., description="New role"),
    user: User = Depends(require_role(["admin"])),
) -> UserInfo:
    """Update user role (admin only)."""
    if username not in DEFAULT_USERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if role not in ["admin", "reviewer", "user"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role",
        )

    DEFAULT_USERS[username]["role"] = role

    return UserInfo(
        id=username,
        name=DEFAULT_USERS[username]["name"],
        role=role,
    )


@router.post(
    "/logout",
    summary="Logout",
    description="Logout (client should discard token)",
)
async def logout() -> dict:
    """Logout (client-side token discard)."""
    return {"message": "Logged out successfully"}