"""Shared configuration for Dispatch backend services.

Loads from environment via pydantic-settings. Doppler injects env vars
at container start; pytest sets them via monkeypatch.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Common settings used by every service that imports this lib."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    host: str = "0.0.0.0"
    port: int = 10060
    db_path: str = "/data/dispatch.db"
    dispatch_tz: str = "Asia/Manila"


@lru_cache
def get_settings() -> Settings:
    """Cached singleton accessor — call this instead of constructing directly."""
    return Settings()
