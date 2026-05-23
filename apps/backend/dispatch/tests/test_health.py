from fastapi.testclient import TestClient


def test_health_endpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("DISPATCH_MASTER_KEY", "test-key")
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    from core import config
    config.get_settings.cache_clear()
    from dispatch.main import app

    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "healthy"
        assert body["service"] == "dispatch-collector"
