"""Tests for the look-back / catch-up synthesis logic in orchestrator.py.

The intent: when the scheduler ticks, it should prefer yesterday if there
is uncovered activity there; otherwise it should walk back through the
look-back window and pick up the oldest day that still needs a brief.
"""
from datetime import date, datetime, timedelta, timezone

import pytest

from dispatch.orchestrator import (
    _is_lead_covered,
    _resolve_target_date,
    find_oldest_uncovered_day_with_activity,
)


def _utc_str(d: date) -> str:
    return f"{d.isoformat()}T12:00:00+00:00"


async def _insert_project(db, slug="fastapi"):
    async with db.cursor() as cur:
        await cur.execute(
            "INSERT INTO projects (slug, display_name, status, kind) VALUES (?, ?, 'active', 'library')",
            (slug, slug.title()),
        )


async def _insert_event(db, slug: str, on_date: date, external_id: str):
    async with db.cursor() as cur:
        await cur.execute(
            """INSERT INTO events (project_slug, kind, external_id, title, author, occurred_at, ingested_at)
               VALUES (?, 'commit', ?, 'event', 'octocat', ?, ?)""",
            (slug, external_id, _utc_str(on_date), _utc_str(on_date)),
        )


async def _insert_filing(db, on_date: date, issue_no: int = 1):
    async with db.cursor() as cur:
        await cur.execute(
            """INSERT INTO filings (date, kind, issue_no, covers_from, covers_until,
                                    lead_headline, lead_body, active_count, project_lines,
                                    model, prompt_hash, generated_at)
               VALUES (?, 'lead', ?, ?, ?, 'h', 'b', 1, '[]', 'kimi', 'p', ?)""",
            (on_date.isoformat(), issue_no,
             f"{on_date.isoformat()}T00:00:00+00:00",
             f"{on_date.isoformat()}T23:59:59+00:00",
             datetime.now(timezone.utc).isoformat()),
        )


@pytest.mark.asyncio
async def test_is_lead_covered_true_when_filing_exists(db):
    await _insert_filing(db, date(2026, 5, 14))
    assert await _is_lead_covered(db, "2026-05-14") is True


@pytest.mark.asyncio
async def test_is_lead_covered_false_when_no_filing(db):
    assert await _is_lead_covered(db, "2026-05-14") is False


@pytest.mark.asyncio
async def test_find_oldest_uncovered_returns_none_when_no_events(db):
    assert await find_oldest_uncovered_day_with_activity(db) is None


@pytest.mark.asyncio
async def test_find_oldest_uncovered_returns_none_when_all_covered(db):
    await _insert_project(db)
    today = datetime.now(timezone.utc).astimezone().date()
    d = today - timedelta(days=3)
    await _insert_event(db, "fastapi", d, "e1")
    await _insert_filing(db, d)
    assert await find_oldest_uncovered_day_with_activity(db) is None


@pytest.mark.asyncio
async def test_find_oldest_uncovered_returns_oldest_uncovered_day(db):
    await _insert_project(db)
    today = datetime.now(timezone.utc).astimezone().date()
    d7 = today - timedelta(days=7)
    d3 = today - timedelta(days=3)
    d1 = today - timedelta(days=1)
    await _insert_event(db, "fastapi", d7, "e7")
    await _insert_event(db, "fastapi", d3, "e3")
    await _insert_event(db, "fastapi", d1, "e1")
    # cover d3 only
    await _insert_filing(db, d3)
    # Expect d7 (oldest uncovered with activity)
    result = await find_oldest_uncovered_day_with_activity(db)
    assert result == d7


@pytest.mark.asyncio
async def test_find_oldest_uncovered_ignores_today(db):
    await _insert_project(db)
    today = datetime.now(timezone.utc).astimezone().date()
    # Activity today should be ignored — we only look at completed days
    await _insert_event(db, "fastapi", today, "etoday")
    assert await find_oldest_uncovered_day_with_activity(db) is None


@pytest.mark.asyncio
async def test_find_oldest_uncovered_respects_look_back_window(db):
    await _insert_project(db)
    today = datetime.now(timezone.utc).astimezone().date()
    very_old = today - timedelta(days=60)
    await _insert_event(db, "fastapi", very_old, "eold")
    # Default look-back is 30 days
    assert await find_oldest_uncovered_day_with_activity(db) is None
    # But a wider window finds it
    assert await find_oldest_uncovered_day_with_activity(db, look_back_days=90) == very_old


# ---------- _resolve_target_date ----------

@pytest.mark.asyncio
async def test_resolve_picks_yesterday_when_active_and_uncovered(db):
    await _insert_project(db)
    today = datetime.now(timezone.utc).astimezone().date()
    yesterday = today - timedelta(days=1)
    await _insert_event(db, "fastapi", yesterday, "ey")
    chosen, reason = await _resolve_target_date(db)
    assert chosen == yesterday.isoformat()
    assert reason == "yesterday"


@pytest.mark.asyncio
async def test_resolve_skips_yesterday_when_already_covered_and_picks_backlog(db):
    await _insert_project(db)
    today = datetime.now(timezone.utc).astimezone().date()
    yesterday = today - timedelta(days=1)
    older = today - timedelta(days=5)
    await _insert_event(db, "fastapi", yesterday, "ey")
    await _insert_event(db, "fastapi", older, "eo")
    await _insert_filing(db, yesterday)
    chosen, reason = await _resolve_target_date(db)
    assert chosen == older.isoformat()
    assert reason == "backlog"


@pytest.mark.asyncio
async def test_resolve_falls_back_to_backlog_when_yesterday_quiet(db):
    await _insert_project(db)
    today = datetime.now(timezone.utc).astimezone().date()
    older = today - timedelta(days=4)
    await _insert_event(db, "fastapi", older, "eo")
    chosen, reason = await _resolve_target_date(db)
    assert chosen == older.isoformat()
    assert reason == "backlog"


@pytest.mark.asyncio
async def test_resolve_returns_none_when_nothing_to_cover(db):
    chosen, reason = await _resolve_target_date(db)
    assert chosen is None
    assert "no events" in reason.lower()
