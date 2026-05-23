"""Smoke tests for the briefing_mentions table — confirms `schema_init.apply`
creates it idempotently and that the PK guards against duplicate rows.
"""
import pytest

from core.db import Database
from dispatch import schema_init


@pytest.mark.asyncio
async def test_briefing_mentions_table_exists_after_init(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    await schema_init.apply(db)
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='briefing_mentions'"
        )
        rows = await cur.fetchall()
    assert len(rows) == 1
    await db.close()


@pytest.mark.asyncio
async def test_briefing_mentions_init_is_idempotent(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    await schema_init.apply(db)
    await schema_init.apply(db)  # second call must not raise
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='briefing_mentions'"
        )
        rows = await cur.fetchall()
    assert len(rows) == 1
    await db.close()


@pytest.mark.asyncio
async def test_briefing_mentions_pk_prevents_duplicates(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    await schema_init.apply(db)
    async with db.cursor() as cur:
        # Seed a parent project — verifies the FK target matches projects(slug).
        await cur.execute(
            "INSERT INTO projects (slug, display_name, status, first_seen_at, last_seen_at) "
            "VALUES ('agos', 'AGOS', 'active', '2026-01-01', '2026-01-01')"
        )
        await cur.execute(
            "INSERT INTO briefing_mentions VALUES ('2026-05-14', 'agos', 'first', 0)"
        )
    # Second insert with the same (date, slug, position) must violate PK.
    with pytest.raises(Exception) as exc_info:
        async with db.cursor() as cur:
            await cur.execute(
                "INSERT INTO briefing_mentions VALUES ('2026-05-14', 'agos', 'second', 0)"
            )
    msg = str(exc_info.value).lower()
    assert "unique constraint failed" in msg or "constraint failed" in msg
    await db.close()
