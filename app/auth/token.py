"""JWT token utilities."""

import os
from datetime import datetime, timedelta
from typing import Optional

import jwt
from pydantic import BaseModel


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # user_id
    role: str
    exp: Optional[datetime] = None


class TokenService:
    """JWT token generation and verification."""

    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60 * 24  # 24 hours

    def create_access_token(self, user_id: str, role: str) -> str:
        """Create JWT access token."""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        payload = {
            "sub": user_id,
            "role": role,
            "exp": expire,
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[TokenPayload]:
        """Verify JWT token and return payload."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return TokenPayload(
                sub=payload.get("sub"),
                role=payload.get("role"),
                exp=datetime.fromtimestamp(payload.get("exp", 0)),
            )
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def decode_token(self, token: str) -> Optional[dict]:
        """Decode token without verification (for logging)."""
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception:
            return None


# Singleton instance
token_service = TokenService()