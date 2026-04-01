"""Password hashing utilities."""

import hashlib
import secrets


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt."""
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${pwd_hash}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    try:
        salt, pwd_hash = hashed.split("$")
        return hashlib.sha256((password + salt).encode()).hexdigest() == pwd_hash
    except Exception:
        return False


# Default users (in production, use a database)
DEFAULT_USERS = {
    "admin": {
        "password": hash_password("admin123"),
        "role": "admin",
        "name": "Administrator",
    },
    "reviewer": {
        "password": hash_password("reviewer123"),
        "role": "reviewer",
        "name": "Reviewer",
    },
    "user": {
        "password": hash_password("user123"),
        "role": "user",
        "name": "Regular User",
    },
}


def get_user(user_id: str) -> dict | None:
    """Get user by ID."""
    return DEFAULT_USERS.get(user_id)


def authenticate(user_id: str, password: str) -> bool:
    """Authenticate user with username and password."""
    user = get_user(user_id)
    if not user:
        return False
    return verify_password(password, user["password"])