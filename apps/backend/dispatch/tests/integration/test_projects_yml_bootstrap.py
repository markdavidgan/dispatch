"""On boot, projects.yml is parsed and synced into the projects table.

Phase 4 replaces this with DB-backed CRUD; until then, the existing
sync_to_db path is load-bearing.
"""
from fastapi.testclient import TestClient


def test_projects_yml_syncs_on_boot(tmp_db_env):
    from dispatch.main import app

    with TestClient(app) as client:
        # /projects is the public list route; after boot it should
        # return >= 1 project from projects.yml.
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        body = resp.json()
        # The response shape is whatever the existing projects.py returns;
        # we only assert the bootstrap ran (non-empty).
        assert body, f"expected projects from projects.yml bootstrap, got: {body!r}"
