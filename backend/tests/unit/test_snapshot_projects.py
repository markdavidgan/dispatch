"""Verifies the snapshot serializer populates project fields.

- projects[].mentioned_in_briefings from the briefing_mentions table.
- projects[].from_the_desk and from_the_desk_generated_at from the projects table.

Per spec §4.1, each project gets up to 5 mentions, newest first, with
{date, excerpt} keys.
"""
import pytest

from dispatch.publish.snapshot import build_snapshot


@pytest.mark.asyncio
async def test_snapshot_projects_include_mentioned_in_briefings(db):
    async with db.cursor() as cur:
        await cur.execute(
            "INSERT INTO projects (slug, display_name, status, first_seen_at, last_seen_at) "
            "VALUES ('agos', 'AGOS', 'active', '2026-01-01T00:00:00Z', '2026-05-14T00:00:00Z')"
        )
        # Six mentions across different dates; only the newest 5 should appear.
        await cur.execute("INSERT INTO briefing_mentions VALUES ('2026-05-14', 'agos', 'AGOS clears the bug.', 0)")
        await cur.execute("INSERT INTO briefing_mentions VALUES ('2026-05-09', 'agos', 'AGOS lands a feature.', 0)")
        await cur.execute("INSERT INTO briefing_mentions VALUES ('2026-04-30', 'agos', 'AGOS ships v0.3.', 0)")
        await cur.execute("INSERT INTO briefing_mentions VALUES ('2026-04-22', 'agos', 'AGOS does the thing.', 0)")
        await cur.execute("INSERT INTO briefing_mentions VALUES ('2026-04-15', 'agos', 'AGOS does another.', 0)")
        await cur.execute("INSERT INTO briefing_mentions VALUES ('2026-04-08', 'agos', 'AGOS sixth one.', 0)")
    await db._conn.commit()

    payload = await build_snapshot(db)
    agos = next(p for p in payload["projects"] if p["slug"] == "agos")
    assert "mentioned_in_briefings" in agos
    assert len(agos["mentioned_in_briefings"]) == 5
    assert agos["mentioned_in_briefings"][0]["date"] == "2026-05-14"     # newest first
    assert agos["mentioned_in_briefings"][0]["excerpt"] == "AGOS clears the bug."
    # Verify the oldest of the top-5 is correct (i.e., the 6th from the bottom is dropped)
    assert agos["mentioned_in_briefings"][-1]["date"] == "2026-04-15"


@pytest.mark.asyncio
async def test_snapshot_projects_with_no_mentions_emit_empty_array(db):
    async with db.cursor() as cur:
        await cur.execute(
            "INSERT INTO projects (slug, display_name, status, first_seen_at, last_seen_at) "
            "VALUES ('marcos', 'Marcos', 'held', '2026-01-01T00:00:00Z', '2026-05-14T00:00:00Z')"
        )
    await db._conn.commit()

    payload = await build_snapshot(db)
    marcos = next(p for p in payload["projects"] if p["slug"] == "marcos")
    assert marcos["mentioned_in_briefings"] == []


@pytest.mark.asyncio
async def test_snapshot_mentions_ordered_by_position_within_a_date(db):
    """Multiple mentions on the same date should respect position ordering
    (the position field of briefing_mentions — secondary sort key)."""
    async with db.cursor() as cur:
        await cur.execute(
            "INSERT INTO projects (slug, display_name, status, first_seen_at, last_seen_at) "
            "VALUES ('agos', 'AGOS', 'active', '2026-01-01T00:00:00Z', '2026-05-14T00:00:00Z')"
        )
        # Two mentions on the same date; position 1 vs 0
        await cur.execute("INSERT INTO briefing_mentions VALUES ('2026-05-14', 'agos', 'second sentence.', 1)")
        await cur.execute("INSERT INTO briefing_mentions VALUES ('2026-05-14', 'agos', 'first sentence.', 0)")
    await db._conn.commit()

    payload = await build_snapshot(db)
    agos = next(p for p in payload["projects"] if p["slug"] == "agos")
    assert len(agos["mentioned_in_briefings"]) == 2
    assert agos["mentioned_in_briefings"][0]["excerpt"] == "first sentence."
    assert agos["mentioned_in_briefings"][1]["excerpt"] == "second sentence."


@pytest.mark.asyncio
async def test_snapshot_projects_include_from_the_desk(db):
    async with db.cursor() as cur:
        await cur.execute(
            "INSERT INTO projects (slug, display_name, status, "
            "from_the_desk, from_the_desk_generated_at, first_seen_at, last_seen_at) "
            "VALUES ('agos', 'AGOS', 'active', 'A productive week.', "
            "'2026-05-11T23:00:00Z', '2026-01-01T00:00:00Z', '2026-05-14T00:00:00Z')"
        )
    await db._conn.commit()

    payload = await build_snapshot(db)
    agos = next(p for p in payload["projects"] if p["slug"] == "agos")
    assert agos["from_the_desk"] == "A productive week."
    assert agos["from_the_desk_generated_at"] == "2026-05-11T23:00:00Z"


@pytest.mark.asyncio
async def test_snapshot_projects_with_null_from_the_desk(db):
    async with db.cursor() as cur:
        await cur.execute(
            "INSERT INTO projects (slug, display_name, status, first_seen_at, last_seen_at) "
            "VALUES ('marcos', 'Marcos', 'held', '2026-01-01T00:00:00Z', '2026-05-14T00:00:00Z')"
        )
    await db._conn.commit()

    payload = await build_snapshot(db)
    marcos = next(p for p in payload["projects"] if p["slug"] == "marcos")
    assert marcos["from_the_desk"] is None
    assert marcos["from_the_desk_generated_at"] is None
