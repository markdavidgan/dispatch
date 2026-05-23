import pytest
from pathlib import Path

from core.db import Database
from dispatch import schema_init
from dispatch.registry.loader import load_yaml, sync_to_db


def test_load_yaml_parses_known_slugs():
    path = Path(__file__).parent.parent.parent / "projects.yml"
    data = load_yaml(path)
    slugs = {p["slug"] for p in data["projects"]}
    assert "agos" in slugs
    assert "aether-focus" in slugs
    assert "marcos" in slugs
    assert "marklab" in slugs
    assert "mark-id" in slugs


@pytest.mark.asyncio
async def test_sync_inserts_then_updates(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    await schema_init.apply(db)

    data = {"projects": [
        {"slug": "agos", "display_name": "Agos", "status": "active", "kind": "app"},
    ]}
    await sync_to_db(db, data)

    async with db.cursor() as cur:
        await cur.execute("SELECT slug, display_name, status FROM projects")
        rows = await cur.fetchall()
    assert rows == [("agos", "Agos", "active")]

    # Update path: re-sync with changed status
    data["projects"][0]["status"] = "held"
    await sync_to_db(db, data)
    async with db.cursor() as cur:
        await cur.execute("SELECT status FROM projects WHERE slug='agos'")
        row = await cur.fetchone()
    assert row[0] == "held"
    await db.close()
