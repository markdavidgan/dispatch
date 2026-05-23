"""Podcast API — list, episodes, manual generate, status."""
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Request, HTTPException, BackgroundTasks

from core.cf_access import verify_cf_access
from dispatch.podcast.registry import load_podcasts, enabled_podcasts
from dispatch.podcast import intake

router = APIRouter(prefix="/podcasts", dependencies=[Depends(verify_cf_access)])


@router.get("")
async def list_podcasts(request: Request) -> dict:
    yml = Path(__file__).parent.parent / "projects.yml"
    casts = load_podcasts(yml)

    # Aggregate per-podcast stats so the frontend index can render episode
    # count + last-published without a per-podcast round-trip.
    db = request.app.state.db
    stats: dict[str, dict] = {}
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT project_slug, COUNT(*) AS episode_count, "
            "       MAX(published_at) AS last_published_at "
            "FROM episodes WHERE status='ready' GROUP BY project_slug"
        )
        for row in await cur.fetchall():
            stats[row[0]] = {"episode_count": row[1], "last_published_at": row[2]}

    return {
        "podcasts": [
            {
                "project_slug": c.project_slug,
                "title": c.title,
                "description": c.description,
                "enabled": c.enabled,
                "feed_url": c.feed_url,
                "episode_count": stats.get(c.project_slug, {}).get("episode_count", 0),
                "last_published_at": stats.get(c.project_slug, {}).get("last_published_at"),
            }
            for c in casts
        ]
    }


@router.get("/{project_slug}/episodes")
async def episodes(project_slug: str, request: Request) -> dict:
    db = request.app.state.db
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT id, episode_no, week_start, title, audio_key, duration_seconds, "
            "       status, published_at "
            "FROM episodes WHERE project_slug=? ORDER BY episode_no DESC",
            (project_slug,),
        )
        cols = ["id","episode_no","week_start","title","audio_key",
                "duration_seconds","status","published_at"]
        rows = [dict(zip(cols, r)) for r in await cur.fetchall()]
    return {"project_slug": project_slug, "episodes": rows}


def _episode_anchor(today: date) -> date:
    """Trailing-7-day anchor for the weekly podcast's coverage window.

    Mirrors scheduler._episode_anchor — keep them in sync.
    """
    return today - timedelta(days=7)


@router.post("/{project_slug}/generate")
async def generate(project_slug: str, request: Request, bg: BackgroundTasks,
                   force: bool = False) -> dict:
    yml = Path(__file__).parent.parent / "projects.yml"
    casts = {c.project_slug: c for c in enabled_podcasts(yml)}
    if project_slug not in casts:
        raise HTTPException(404, f"no enabled podcast for {project_slug}")
    podcast = casts[project_slug]
    tz = os.environ.get("DISPATCH_TZ", "Asia/Manila")
    today = datetime.now(timezone.utc).astimezone(ZoneInfo(tz)).date()
    week_start = _episode_anchor(today)

    db = request.app.state.db
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT id, status FROM episodes WHERE project_slug=? AND week_start=?",
            (project_slug, week_start.isoformat()),
        )
        existing = await cur.fetchone()
    if existing and not force and existing[1] in ("composing", "awaiting_nblm", "downloading", "ready"):
        raise HTTPException(409, f"episode already exists for {week_start} (status={existing[1]})")

    bg.add_task(intake.run_episode, db, podcast, week_start)
    return {"status": "queued", "project_slug": project_slug, "week_start": week_start.isoformat()}
