"""Registration, login and the current-user endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _token_response(user: User) -> TokenResponse:
    token, expires_in = create_access_token(user.id)
    return TokenResponse(
        access_token=token, expires_in=expires_in, user=UserOut.model_validate(user)
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = _normalize_email(payload.email)

    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="email already registered"
        )

    try:
        password_hash = hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    user = User(
        email=email,
        display_name=payload.display_name.strip(),
        password_hash=password_hash,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:  # lost the race against a concurrent signup
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="email already registered"
        ) from exc

    db.refresh(user)
    return _token_response(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = _normalize_email(payload.email)
    user = db.scalar(select(User).where(User.email == email))

    # Same error for unknown email and wrong password: do not leak which
    # addresses have accounts.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="account disabled"
        )

    return _token_response(user)


@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
