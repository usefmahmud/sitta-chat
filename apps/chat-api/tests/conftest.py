"""Test fixtures.

The environment is configured *before* the app package is imported so the
engine points at a throwaway database instead of the developer's data file.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

_tmpdir = Path(tempfile.mkdtemp(prefix="sitta-chat-tests-"))
os.environ["CHAT_ENVIRONMENT"] = "test"
os.environ["CHAT_DATABASE_URL"] = f"sqlite:///{_tmpdir / 'test.db'}"
os.environ["CHAT_SECRET_KEY"] = "test-secret-key-not-for-production"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import create_app  # noqa: E402


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
