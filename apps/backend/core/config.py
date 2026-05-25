"""Shared configuration for Dispatch backend services.

Loads from environment via pydantic-settings.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Common settings used by every service that imports this lib."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    host: str = "0.0.0.0"
    port: int = 10060
    db_path: str = "/data/dispatch.db"
    dispatch_tz: str = "Asia/Manila"
    # Mandatory: encrypts settings at rest.
    # validation_alias pins the env var name to DISPATCH_MASTER_KEY
    # instead of the pydantic-settings default of MASTER_KEY.
    master_key: str | None = Field(
        default=None,
        validation_alias="DISPATCH_MASTER_KEY",
    )
    # Comma-separated list of additional CORS origins (e.g.
    # "https://app.example.com,https://staging.example.com").
    # Primarily used for split deployments where the SPA is hosted on
    # a different origin than the backend.
    cors_origins: str = Field(default="", validation_alias="DISPATCH_CORS_ORIGINS")


@lru_cache
def get_settings() -> Settings:
    """Cached singleton accessor — call this instead of constructing directly."""
    return Settings()
