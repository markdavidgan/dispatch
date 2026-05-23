"""Smoke test: the app boots, lifespan completes, /health responds.

Uses FastAPI's TestClient which drives the lifespan context manager
end-to-end (DB connect, schema apply, scheduler start, projects.yml sync).
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_db_env(tmp_path, monkeypatch):
    """Point the app at a tempdir SQLite file and disable APScheduler timing."""
    db_path = tmp_path / "dispatch.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    # Phase 1 introduces this as a boot-gate (no encryption use yet).
    monkeypatch.setenv("DISPATCH_MASTER_KEY", "test-key-not-secret")
    # Force a fresh Settings() — the singleton caches across tests otherwise.
    from core import config
    config.get_settings.cache_clear()
    yield db_path
    config.get_settings.cache_clear()


def test_app_boots_and_health_responds(tmp_db_env):
    from dispatch.main import app

    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["service"] == "dispatch-collector"
        assert body["db_ok"] is True
