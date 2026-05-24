"""Standalone mode trusts the deployment perimeter, not Cf-Access headers.

After Task 4 removes the cf_access dependency, GET /live (and the other
previously-protected routes) must respond 200 with no special headers.
"""
from fastapi.testclient import TestClient


def test_live_does_not_require_cf_headers(tmp_db_env):
    from dispatch.main import app

    with TestClient(app) as client:
        resp = client.get("/api/live")
        # Acceptable: 200 (empty event set returns {} or similar).
        # Unacceptable: 401 (the cf_access "credentials required" response).
        assert resp.status_code != 401, (
            "Standalone backend must not require Cf-Access headers. "
            "If you see 401, the cf_access dependency was not removed."
        )


def test_brief_post_does_not_require_cf_headers(tmp_db_env):
    from dispatch.main import app

    with TestClient(app) as client:
        # /brief endpoints are POST in the existing code; we don't care
        # about response shape here, only that auth doesn't block us.
        resp = client.post("/api/brief/refresh")
        assert resp.status_code != 401


def test_projects_does_not_require_cf_headers(tmp_db_env):
    from dispatch.main import app

    with TestClient(app) as client:
        resp = client.get("/api/projects")
        assert resp.status_code != 401


def test_podcasts_does_not_require_cf_headers(tmp_db_env):
    from dispatch.main import app

    with TestClient(app) as client:
        resp = client.get("/api/podcasts")
        assert resp.status_code != 401
