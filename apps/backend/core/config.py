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
    # Mandatory: encrypts settings at rest from Phase 3 onward.
    # Phase 1 validates presence only; no encryption is performed yet.
    # validation_alias pins the env var name to DISPATCH_MASTER_KEY
    # instead of the pydantic-settings default of MASTER_KEY.
    master_key: str | None = Field(
        default=None,
        validation_alias="DISPATCH_MASTER_KEY",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
