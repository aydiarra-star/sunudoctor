"""Password hashing and JWT helpers.

Notes:
- Passwords are hashed with bcrypt (never stored in clear).
- bcrypt is used directly rather than through passlib: passlib 1.7.4 probes a
  ``bcrypt.__about__`` attribute that was removed in bcrypt 4.x, which makes it
  log a traceback on first use. Calling bcrypt directly is stable across
  versions and avoids that failure mode in production.
- bcrypt truncates at 72 bytes; inputs are validated to a smaller maximum at the
  schema layer, and this guard prevents silent truncation here too.
- Access tokens are short-lived JWTs; refresh tokens are separate.
- No secret is hardcoded here; the signing key comes from settings.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

_BCRYPT_MAX_BYTES = 72


def _prepare(password: str) -> bytes:
    raw = password.encode("utf-8")
    if len(raw) > _BCRYPT_MAX_BYTES:
        # Never silently truncate a credential; refuse it instead.
        raise ValueError("Mot de passe trop long (maximum 72 octets).")
    return raw


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _create_token(subject: str, expires_delta: timedelta, token_type: str, **claims) -> str:
    now = datetime.now(UTC)
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
    "JWTError",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "hash_password",
    "verify_password",
]
