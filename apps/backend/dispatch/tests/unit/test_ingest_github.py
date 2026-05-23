import pytest
import respx
import httpx
from core.db import Database
from dispatch import schema_init
from dispatch.registry.loader import sync_to_db
from dispatch.ingest.github import ingest_repo


@pytest.mark.asyncio
async def test_ingest_pulls_and_writes_prs(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "fake")
    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    await schema_init.apply(db)
    await sync_to_db(db, {"projects": [
        {"slug": "agos", "display_name": "Agos", "status": "active",
         "kind": "app", "github": "markdavidgan/agos"},
    ]})

    pulls_payload = [
        {"id": 1, "number": 42, "title": "Refactor podcast",
         "user": {"login": "markdavidgan"},
         "html_url": "https://github.com/markdavidgan/agos/pull/42",
         "created_at": "2026-05-13T14:30:00Z",
         "updated_at": "2026-05-13T15:00:00Z",
         "merged_at": "2026-05-13T16:00:00Z",
         "state": "closed"},
    ]
    issues_payload = []
    releases_payload = []

    with respx.mock(base_url="https://api.github.com") as mock:
        mock.get("/repos/markdavidgan/agos/pulls").mock(
            return_value=httpx.Response(200, json=pulls_payload))
        mock.get("/repos/markdavidgan/agos/issues").mock(
            return_value=httpx.Response(200, json=issues_payload))
        mock.get("/repos/markdavidgan/agos/releases").mock(
            return_value=httpx.Response(200, json=releases_payload))
        n = await ingest_repo(db, slug="agos", repo="markdavidgan/agos")

    assert n >= 1
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT kind, external_id, title FROM events WHERE project_slug='agos'")
        rows = await cur.fetchall()
    kinds = {r[0] for r in rows}
    assert "pr_merged" in kinds
    assert "pr_opened" in kinds
    await db.close()
