"""Application settings.

Every setting is read from the environment with the ``CHAT_`` prefix, so the
same image runs in dev, test and prod without code changes.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    secret_key: str = "dev-only-insecure-secret-change-me"
    access_token_ttl_minutes: int = 60

    cors_origins: list[str] = ["http://localhost:5173"]

    @property
    def is_testing(self) -> bool:
        return self.environment == "test"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings (cached, so tests can clear it)."""
    return Settings()
