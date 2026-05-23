"""Shared fixtures for integration tests."""
import pytest


@pytest.fixture
def tmp_db_env(tmp_path, monkeypatch):
    """Point the app at a tempdir SQLite file and provide the boot-gate key."""
    db_path = tmp_path / "dispatch.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("DISPATCH_MASTER_KEY", "test-key-not-secret")
    from core import config
    config.get_settings.cache_clear()
    yield db_path
    config.get_settings.cache_clear()
