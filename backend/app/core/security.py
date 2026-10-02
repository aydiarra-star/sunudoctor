"""Password hashing and JWT helpers.

Notes:
- Passwords are hashed with bcrypt (never stored in clear).
- Access tokens are short-lived JWTs; refresh tokens are separate.
- No secret is hardcoded here; the signing key comes from settings.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(subject: str, expires_delta: timedelta, token_type: str, **claims) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "type": token_type,
        **claims,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_access_token(subject: str, role: str) -> str:
    return _create_token(
        subject,
        timedelta(minutes=settings.access_token_expire_minutes),
        "access",
        role=role,
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject, timedelta(days=settings.refresh_token_expire_days), "refresh"
    )


def decode_token(token: str) -> dict:
    """Return the token payload or raise JWTError."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "JWTError",
]
