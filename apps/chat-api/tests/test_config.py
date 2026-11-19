"""Settings must fail closed: no secret means no start outside development."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_without_a_secret_refuses_to_start():
    with pytest.raises(ValidationError):
        Settings(environment="production", secret_key="")


def test_production_with_the_example_placeholder_refuses_to_start():
    with pytest.raises(ValidationError):
        Settings(environment="production", secret_key="change-me-before-you-start")


def test_production_with_a_short_secret_refuses_to_start():
    with pytest.raises(ValidationError):
        Settings(environment="production", secret_key="short")


def test_production_accepts_a_real_secret():
    secret = "a" * 64
    settings = Settings(environment="production", secret_key=secret)

    assert settings.secret_key == secret


def test_development_gets_an_ephemeral_secret():
    settings = Settings(environment="development", secret_key="")

    assert len(settings.secret_key) >= 32
    assert "change-me" not in settings.secret_key
