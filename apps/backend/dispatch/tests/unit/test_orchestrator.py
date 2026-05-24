"""Unit tests for orchestrator helpers."""
import pytest
from dispatch.orchestrator import _events_for_window, _project_input


@pytest.mark.asyncio
async def test_events_for_window(db):
    async with db.cursor() as cur:
        await cur.execute(
            "INSERT INTO projects (slug, display_name, status, kind) VALUES (?, ?, ?, ?)",
            ("fastapi", "FastAPI", "active", "library"),
        )
        await cur.execute(
            """INSERT INTO events (project_slug, kind, external_id, title, author, occurred_at, ingested_at)
               VALUES (?, 'commit', 'abc', 'Fix bug', 'octocat', '2026-05-14T10:00:00Z', '2026-05-14T10:01:00Z')""",
            ("fastapi",),
        )

    events = await _events_for_window(db, "2026-05-14T00:00:00Z", "2026-05-14T23:59:59Z")
    assert "fastapi" in events
    assert len(events["fastapi"]) == 1
    assert events["fastapi"][0]["kind"] == "commit"


@pytest.mark.asyncio
async def test_project_input_derives_bullets(db):
    events = {
        "claude-code": [
            {"kind": "commit", "title": "fix"},
            {"kind": "commit", "title": "feat"},
            {"kind": "commit", "title": "docs"},
        ]
    }
    projects = await _project_input(db, events)
    cc = next((p for p in projects if p["slug"] == "claude-code"), None)
    assert cc is not None
    assert cc["bullet"] == "red"
    assert "3 commits" in cc["stat"]
