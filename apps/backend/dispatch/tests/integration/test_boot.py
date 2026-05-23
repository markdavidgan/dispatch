"""Smoke test: the app boots, lifespan completes, /health responds."""
from fastapi.testclient import TestClient


def test_app_boots_and_health_responds(tmp_db_env):
    from dispatch.main import app

    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["service"] == "dispatch-collector"
        assert body["db_ok"] is True
