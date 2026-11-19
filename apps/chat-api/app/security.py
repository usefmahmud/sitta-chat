"""Password hashing and JWT access tokens.

bcrypt for passwords (salted, slow by design), HS256 JWTs signed with
``CHAT_SECRET_KEY`` for stateless auth. Nothing here touches the database.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import get_settings

ALGORITHM = "HS256"

# bcrypt only reads the first 72 bytes; refuse longer input instead of
# silently truncating a password.
MAX_PASSWORD_BYTES = 72


class TokenError(Exception):
    """A token was missing, malformed, expired or signed with another key."""


def _password_bytes(password: str) -> bytes:
    raw = password.encode("utf-8")
    if len(raw) > MAX_PASSWORD_BYTES:
        raise ValueError(f"password must be at most {MAX_PASSWORD_BYTES} bytes")
    return raw


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_password_bytes(password), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, ttl_minutes: int | None = None) -> tuple[str, int]:
    """Return ``(token, expires_in_seconds)`` for the given user id."""
    settings = get_settings()
    ttl = settings.access_token_ttl_minutes if ttl_minutes is None else ttl_minutes
    now = datetime.now(timezone.utc)
    payload = {"sub": subject, "iat": now, "exp": now + timedelta(minutes=ttl)}
    token = jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)
    return token, ttl * 60


def decode_access_token(token: str) -> str:
    """Return the subject (user id) or raise :class:`TokenError`."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:  # expired, bad signature, garbage
        raise TokenError(str(exc)) from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise TokenError("token has no subject")
    return subject
