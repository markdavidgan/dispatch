"""Unit tests for API routes — tested directly without ASGI transport.

We call the route handler coroutines with mocked Request objects
because TestClient/ASGITransport in starlette 0.41.x do not handle
lifespan state reliably in this container environment.
"""
import pytest
from unittest.mock import MagicMock

from core.db import Database
from dispatch import schema_init
from dispatch.api.health import health
from dispatch.api.live import live
from dispatch.api.projects import list_projects
from dispatch.api.brief import refresh


@pytest.fixture
def mock_request(db):
    req = MagicMock()
    req.app.state.db = db
    return req


@pytest.mark.asyncio
async def test_health_direct(mock_request):
    r = await health(mock_request)
    assert r["status"] == "healthy"
    assert r["service"] == "dispatch-collector"


@pytest.mark.asyncio
async def test_live_direct(mock_request, monkeypatch):
    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", "test-id")
    monkeypatch.setenv("CF_ACCESS_CLIENT_SECRET", "test-secret")
    r = await live(mock_request)
    assert "as_of" in r
    assert "projects" in r


@pytest.mark.asyncio
async def test_projects_direct(mock_request):
    # Seed a project
    async with mock_request.app.state.db.cursor() as cur:
        await cur.execute(
            "INSERT INTO projects (slug, display_name, status, kind) VALUES (?, ?, ?, ?)",
            ("agos", "Agos", "active", "app"),
        )
    r = await list_projects(mock_request)
    assert len(r) == 1
    assert r[0]["slug"] == "agos"


@pytest.mark.asyncio
async def test_brief_refresh_raises_without_lead(mock_request):
    with pytest.raises(Exception):
        await refresh(mock_request)
