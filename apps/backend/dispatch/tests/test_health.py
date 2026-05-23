from fastapi.testclient import TestClient
from dispatch.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "healthy"
        assert body["service"] == "dispatch-collector"
