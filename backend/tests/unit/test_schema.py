import pytest

from core.db import Database
from dispatch import schema_init


@pytest.mark.asyncio
async def test_schema_creates_expected_tables(tmp_path):
    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    await schema_init.apply(db)
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        rows = await cur.fetchall()
    names = [r[0] for r in rows]
    assert "projects" in names
    assert "events" in names
    assert "cursors" in names
    assert "filings" in names
    assert "runs" in names
    assert "episodes" in names
    await db.close()


@pytest.mark.asyncio
async def test_schema_is_idempotent(tmp_path):
    """Applying twice should not error."""
    db = Database(str(tmp_path / "t.db"))
    await db.connect()
    await schema_init.apply(db)
    await schema_init.apply(db)
    await db.close()
