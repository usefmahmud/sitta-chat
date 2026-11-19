"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import User
from .security import TokenError, decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTHORIZED = {"WWW-Authenticate": "Bearer"}


def _unauthorized(detail: str = "invalid or expired token") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers=_UNAUTHORIZED
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _unauthorized("missing bearer token")
    try:
        user_id = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise _unauthorized() from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized()
    return user
