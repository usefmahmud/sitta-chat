"""Application settings.

Every setting is read from the environment with the ``CHAT_`` prefix, so the
same image runs in dev, test and prod without code changes.
"""

from __future__ import annotations

import secrets
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PLACEHOLDER_MARKERS = ("change", "-only", "insecure")
MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CHAT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "sitta-chat-api"
    version: str = "0.1.0"
    environment: str = "development"

    database_url: str = "sqlite:///./data/chat.db"
    # No default secret: development gets an ephemeral one, anything else
    # must be supplied by the environment or the app refuses to start.
    secret_key: str = ""
    access_token_ttl_minutes: int = 60

    cors_origins: list[str] = ["http://localhost:5173"]

    @property
    def is_testing(self) -> bool:
        return self.environment == "test"

    @model_validator(mode="after")
    def _resolve_secret_key(self) -> "Settings":
        key = self.secret_key.strip()

        if self.environment == "development":
            if not key or _looks_like_placeholder(key):
                # Ephemeral per process: tokens die on restart, which is
                # exactly what a dev box wants, and nothing weak ships.
                self.secret_key = secrets.token_urlsafe(48)
            return self

        if not key:
            raise ValueError(
                "CHAT_SECRET_KEY is required when CHAT_ENVIRONMENT is not "
                "'development' (generate one with: openssl rand -hex 32)"
            )
        if _looks_like_placeholder(key):
            raise ValueError("CHAT_SECRET_KEY is still the example placeholder")
        if len(key) < MIN_SECRET_LENGTH:
            raise ValueError(
                f"CHAT_SECRET_KEY must be at least {MIN_SECRET_LENGTH} characters"
            )
        self.secret_key = key
        return self


def _looks_like_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings (cached, so tests can clear it)."""
    return Settings()
