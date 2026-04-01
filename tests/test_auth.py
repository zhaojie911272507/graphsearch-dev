"""Tests for authentication module."""

import pytest
from app.auth.token import TokenService, token_service
from app.auth.password import hash_password, verify_password, authenticate, DEFAULT_USERS
from app.auth.roles import Role, has_permission


class TestTokenService:
    """Tests for JWT token service."""

    def test_create_access_token(self):
        """Test creating JWT access token."""
        token = token_service.create_access_token("test_user", "admin")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_valid_token(self):
        """Test verifying a valid token."""
        token = token_service.create_access_token("test_user", "admin")
        payload = token_service.verify_token(token)

        assert payload is not None
        assert payload.sub == "test_user"
        assert payload.role == "admin"

    def test_verify_invalid_token(self):
        """Test verifying an invalid token."""
        payload = token_service.verify_token("invalid_token")
        assert payload is None

    def test_verify_tampered_token(self):
        """Test verifying a tampered token."""
        token = token_service.create_access_token("test_user", "admin")
        tampered = token + "tampered"
        payload = token_service.verify_token(tampered)
        assert payload is None


class TestPasswordService:
    """Tests for password utilities."""

    def test_hash_password(self):
        """Test password hashing."""
        hashed = hash_password("test_password")
        assert hashed is not None
        assert "$" in hashed  # Salt$Hash format
        assert len(hashed) > 20

    def test_verify_correct_password(self):
        """Test verifying correct password."""
        password = "test_password"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """Test verifying wrong password."""
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_authenticate_valid(self):
        """Test authenticating valid user."""
        # Use default users
        assert authenticate("admin", "admin123") is True
        assert authenticate("reviewer", "reviewer123") is True
        assert authenticate("user", "user123") is True

    def test_authenticate_invalid(self):
        """Test authenticating invalid user."""
        assert authenticate("admin", "wrong_password") is False
        assert authenticate("nonexistent", "password") is False


class TestRolePermissions:
    """Tests for role-based access control."""

    def test_admin_has_all_permissions(self):
        """Test admin has all permissions."""
        assert has_permission("admin", "assets:read") is True
        assert has_permission("admin", "assets:write") is True
        assert has_permission("admin", "ontology:read") is True
        assert has_permission("admin", "ontology:write") is True
        assert has_permission("admin", "ontology:delete") is True
        assert has_permission("admin", "review:read") is True
        assert has_permission("admin", "review:write") is True
        assert has_permission("admin", "users:read") is True
        assert has_permission("admin", "users:write") is True

    def test_reviewer_has_limited_permissions(self):
        """Test reviewer has limited permissions."""
        assert has_permission("reviewer", "assets:read") is True
        assert has_permission("reviewer", "assets:write") is False
        assert has_permission("reviewer", "ontology:read") is True
        assert has_permission("reviewer", "users:read") is False

    def test_user_has_minimal_permissions(self):
        """Test user has minimal permissions."""
        assert has_permission("user", "assets:read") is True
        assert has_permission("user", "assets:write") is False
        assert has_permission("user", "users:read") is False


class TestDefaultUsers:
    """Tests for default users."""

    def test_default_users_exist(self):
        """Test default users are configured."""
        assert "admin" in DEFAULT_USERS
        assert "reviewer" in DEFAULT_USERS
        assert "user" in DEFAULT_USERS

    def test_default_user_roles(self):
        """Test default user roles."""
        assert DEFAULT_USERS["admin"]["role"] == "admin"
        assert DEFAULT_USERS["reviewer"]["role"] == "reviewer"
        assert DEFAULT_USERS["user"]["role"] == "user"

    def test_get_user(self):
        """Test getting user by ID."""
        from app.auth.password import get_user

        user = get_user("admin")
        assert user is not None
        assert user["role"] == "admin"

        user = get_user("nonexistent")
        assert user is None