"""Tests for the dispatch-wide weekly podcast composer.

The dispatch-weekly podcast differs from per-project podcasts in that
the source material is the week's *curated lead briefings* — not raw
GitHub events. NotebookLM weaves cross-project themes from already-
narrative input.
"""
from datetime import date, datetime, timedelta, timezone

import pytest

from dispatch.podcast.composer import (
    DISPATCH_WEEKLY_SLUG,
    compose_dispatch_weekly,
)


async def _insert_lead(db, on_date: date, issue_no: int, headline: str, article: str):
    async with db.cursor() as cur:
        await cur.execute(
            """INSERT INTO filings (date, kind, issue_no, covers_from, covers_until,
                                    lead_headline, lead_body, lead_article, active_count,
                                    project_lines, model, prompt_hash, generated_at)
               VALUES (?, 'lead', ?, ?, ?, ?, 'body', ?, 3, '[]', 'kimi', 'p', ?)""",
            (on_date.isoformat(), issue_no,
             f"{on_date.isoformat()}T00:00:00+00:00",
             f"{on_date.isoformat()}T23:59:59+00:00",
             headline, article,
             datetime.now(timezone.utc).isoformat()),
        )


def test_slug_constant_is_stable():
    # intake.run_episode branches on this; pin it so refactors break loudly.
    assert DISPATCH_WEEKLY_SLUG == "dispatch-weekly"


@pytest.mark.asyncio
async def test_compose_includes_every_brief_in_window(db):
    week_start = date(2026, 5, 18)  # Monday
    await _insert_lead(db, date(2026, 5, 19), 1, "Tuesday headline", "Tuesday article body.")
    await _insert_lead(db, date(2026, 5, 21), 2, "Thursday headline", "Thursday article body.")
    await _insert_lead(db, date(2026, 5, 24), 3, "Sunday headline", "Sunday article body.")

    md = await compose_dispatch_weekly(db, week_start, window_days=7, episode_no=4)

    assert "Tuesday headline" in md
    assert "Thursday headline" in md
    assert "Sunday headline" in md
    assert "Tuesday article body." in md
    assert "Episode 4" in md


@pytest.mark.asyncio
async def test_compose_excludes_briefs_outside_window(db):
    week_start = date(2026, 5, 18)
    # Within window
    await _insert_lead(db, date(2026, 5, 20), 1, "In window", "x")
    # One day before window
    await _insert_lead(db, date(2026, 5, 17), 99, "Before window", "y")
    # One day after the 7-day window (week_start + 7 = 2026-05-25 is exclusive)
    await _insert_lead(db, date(2026, 5, 25), 100, "After window", "z")

    md = await compose_dispatch_weekly(db, week_start, window_days=7, episode_no=1)
    assert "In window" in md
    assert "Before window" not in md
    assert "After window" not in md


@pytest.mark.asyncio
async def test_compose_returns_friendly_empty_when_no_briefs(db):
    week_start = date(2026, 5, 18)
    md = await compose_dispatch_weekly(db, week_start, window_days=7, episode_no=1)
    assert "No briefings filed this week." in md


@pytest.mark.asyncio
async def test_compose_prefers_lead_article_over_lead_body(db):
    """When lead_article is present (the long-form text), it is what
    NotebookLM should receive — not the shorter dek."""
    week_start = date(2026, 5, 18)
    await _insert_lead(db, date(2026, 5, 20), 1, "Headline",
                       "Long-form article paragraph with detail.")
    md = await compose_dispatch_weekly(db, week_start)
    assert "Long-form article paragraph with detail." in md
