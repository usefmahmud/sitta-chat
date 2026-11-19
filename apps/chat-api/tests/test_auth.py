"""Auth: register, login, and the JWT-protected /me endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.security import create_access_token, hash_password, verify_password

PASSWORD = "correct-horse-9"


def test_register_returns_token_and_user(client: TestClient):
    response = client.post(
        "/api/auth/register",
        json={"email": "New.User@Example.com", "password": PASSWORD, "display_name": "New User"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["access_token"]
    assert body["user"]["email"] == "new.user@example.com"  # normalised
    assert body["user"]["display_name"] == "New User"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]


def test_register_stores_a_bcrypt_hash_not_the_password(client: TestClient):
    client.post(
        "/api/auth/register",
        json={"email": "hash@example.com", "password": PASSWORD, "display_name": "Hash"},
    )

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "hash@example.com"))

    assert user is not None
    assert user.password_hash != PASSWORD
    assert user.password_hash.startswith("$2")
    assert verify_password(PASSWORD, user.password_hash)


def test_register_rejects_duplicate_email(client: TestClient, register):
    assert register("dup@example.com").status_code == 201

    duplicate = register("DUP@example.com")  # same address, different case

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "email already registered"


def test_register_rejects_invalid_email(client: TestClient):
    response = client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": PASSWORD, "display_name": "X"},
    )
    assert response.status_code == 422


def test_register_rejects_short_password(client: TestClient):
    response = client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "password": "1234", "display_name": "X"},
    )
    assert response.status_code == 422


def test_login_returns_a_working_token(client: TestClient, register):
    register("login@example.com")

    response = client.post(
        "/api/auth/login", json={"email": "login@example.com", "password": PASSWORD}
    )

    assert response.status_code == 200
    token = response.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "login@example.com"


def test_login_rejects_wrong_password(client: TestClient, register):
    register("wrong@example.com")

    response = client.post(
        "/api/auth/login", json={"email": "wrong@example.com", "password": "not-my-password"}
    )

    assert response.status_code == 401


def test_login_rejects_unknown_email(client: TestClient):
    response = client.post(
        "/api/auth/login", json={"email": "ghost@example.com", "password": PASSWORD}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "invalid email or password"


def test_me_requires_a_token(client: TestClient):
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_rejects_a_garbage_token(client: TestClient):
    response = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer not.a.jwt"}
    )
    assert response.status_code == 401


def test_me_rejects_an_expired_token(client: TestClient, register):
    register("expired@example.com")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "expired@example.com"))
    assert user is not None

    expired, _ = create_access_token(user.id, ttl_minutes=-1)
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401


def test_me_returns_the_current_user(client: TestClient, auth_headers):
    response = client.get("/api/auth/me", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "omar@example.com"
    assert set(body) == {"id", "email", "display_name", "created_at"}


def test_hash_password_rejects_over_72_bytes():
    import pytest

    with pytest.raises(ValueError):
        hash_password("a" * 73)
