"""Test fixtures.

The environment is configured *before* the app package is imported so the
engine points at a throwaway database instead of the developer's data file.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path

_tmpdir = Path(tempfile.mkdtemp(prefix="sitta-chat-tests-"))
os.environ["CHAT_ENVIRONMENT"] = "test"
os.environ["CHAT_DATABASE_URL"] = f"sqlite:///{_tmpdir / 'test.db'}"
os.environ["CHAT_SECRET_KEY"] = "test-secret-key-not-for-production"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from httpx import Response  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import create_app  # noqa: E402

DEFAULT_PASSWORD = "correct-horse-9"


@pytest.fixture(autouse=True)
def _schema() -> Iterator[None]:
    """Every test starts from an empty schema."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def register(client: TestClient) -> Callable[..., Response]:
    """Register a user; call it again with another email for a second account."""

    def _register(
        email: str = "omar@example.com",
        password: str = DEFAULT_PASSWORD,
        display_name: str = "Omar",
    ) -> Response:
        return client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": password,
                "display_name": display_name,
            },
        )

    return _register


@pytest.fixture
def access_token(register: Callable[..., Response]) -> str:
    response = register()
    assert response.status_code == 201, response.text
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}
