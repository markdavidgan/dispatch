"""Admin podcast endpoints — manual compose triggers.

The scheduler runs a weekly job for every enabled podcast. These endpoints
let operators kick a compose immediately (or re-compose after editing
projects.yml) without waiting for the next scheduled tick.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from dispatch.podcast import composer, intake
from dispatch.podcast.registry import load_podcasts

router = APIRouter(prefix="/admin/podcasts")
log = logging.getLogger(__name__)

PROJECTS_YML = Path(__file__).parent.parent.parent / "projects.yml"


def _week_start_for(today: date | None = None) -> date:
    """Sliding 7-day window ending *yesterday* (in UTC).

    Manual triggers always want the most recent 7 days of activity; using
    a calendar-week anchor would show "empty" early in the week. The
    scheduled Saturday-morning compose hits the same sliding window — Sat
    covers Sun–Sat, the natural editorial week.
    """
    today = today or datetime.now(timezone.utc).date()
    return today - timedelta(days=7)


@router.post("/{slug}/compose")
async def compose_now(request: Request, slug: str) -> dict:
    """Trigger a fresh compose of the given podcast for this week.

    Works for both single-project podcasts and the dispatch-wide weekly
    aggregate (`slug=dispatch-weekly`). Returns the episode_id (or null if
    the run was skipped — typically because NotebookLM creds aren't set).
    """
    db = request.app.state.db
    podcasts = {p.project_slug: p for p in load_podcasts(PROJECTS_YML)}
    if slug not in podcasts:
        raise HTTPException(404, detail=f"no podcast config for slug {slug!r}")

    week_start = _week_start_for()
    try:
        episode_id = await intake.run_episode(db, podcasts[slug], week_start)
    except Exception as e:
        log.exception("podcast compose failed for %s", slug)
        raise HTTPException(503, detail=f"compose failed: {e}")

    return {
        "slug": slug,
        "week_start": week_start.isoformat(),
        "episode_id": episode_id,
        "note": (
            "episode_id=null means the run was skipped — usually because "
            "the NotebookLM session token isn't configured under "
            "/admin/settings (podcast.notebooklm_session)."
        ) if episode_id is None else None,
    }


@router.get("/{slug}/preview-source")
async def preview_source(request: Request, slug: str) -> dict:
    """Return the markdown that would be sent to NotebookLM for *slug*'s
    next compose, without actually composing. Useful for tuning prompts /
    seeing what the podcast will be built from."""
    db = request.app.state.db
    podcasts = {p.project_slug: p for p in load_podcasts(PROJECTS_YML)}
    if slug not in podcasts:
        raise HTTPException(404, detail=f"no podcast config for slug {slug!r}")
    podcast = podcasts[slug]
    week_start = _week_start_for()
    if slug == composer.DISPATCH_WEEKLY_SLUG:
        md = await composer.compose_dispatch_weekly(
            db, week_start, podcast.compose_window_days, episode_no=0,
        )
    else:
        md = await composer.compose(
            db, podcast.project_slug, podcast.title, podcast.project_slug,
            week_start, podcast.compose_window_days, episode_no=0,
        )
    return {
        "slug": slug,
        "week_start": week_start.isoformat(),
        "source_markdown": md,
        "chars": len(md),
    }
