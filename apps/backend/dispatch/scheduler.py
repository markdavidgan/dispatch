"""APScheduler wiring — ingest, synthesis, publish, audio, podcast, housekeeping.

All jobs run in-process. Jittered start avoids thundering herd.
"""
from __future__ import annotations

import logging
import os
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from core.db import Database
from dispatch import orchestrator
from dispatch.synthesis.from_the_desk import generate_from_the_desk
from dispatch.podcast.registry import enabled_podcasts
from dispatch.podcast import intake
from dispatch.publish.r2 import delete_object, list_objects

log = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=os.environ.get("DISPATCH_TZ", "Asia/Manila"))
    return _scheduler


def _jittered_minute() -> int:
    return random.randint(0, 59)


def start_jobs(db: Database) -> None:
    sched = get_scheduler()
    tz = os.environ.get("DISPATCH_TZ", "Asia/Manila")

    # Ingest: git every 15 min
    sched.add_job(
        orchestrator.run_ingest_git,
        IntervalTrigger(minutes=15, jitter=60),
        args=[db],
        id="ingest_git",
        replace_existing=True,
    )

    # Ingest: github every 30 min
    sched.add_job(
        orchestrator.run_ingest_github,
        IntervalTrigger(minutes=30, jitter=60),
        args=[db],
        id="ingest_github",
        replace_existing=True,
    )

    # Synthesis: lead daily at 02:00
    sched.add_job(
        _synthesis_lead_pipeline,
        CronTrigger(hour=2, minute=_jittered_minute(), timezone=tz),
        args=[db],
        id="synthesis_lead",
        replace_existing=True,
    )

    # Housekeeping: daily 03:30
    sched.add_job(
        _housekeeping,
        CronTrigger(hour=3, minute=30, timezone=tz),
        args=[db],
        id="housekeeping",
        replace_existing=True,
    )

    # From-the-desk: weekly summary per active+held project (Sunday 23:00)
    sched.add_job(
        _from_the_desk_weekly,
        CronTrigger(day_of_week="sun", hour=23, minute=_jittered_minute(), timezone=tz),
        args=[db],
        id="synthesis:from_the_desk",
        replace_existing=True,
    )

    # Podcasts: one weekly job per enabled podcast
    projects_yml = Path(__file__).parent / "projects.yml"
    for podcast in enabled_podcasts(projects_yml):
        parts = podcast.cron.split()
        if len(parts) != 5:
            log.warning("invalid cron for %s: %s — skipping", podcast.project_slug, podcast.cron)
            continue
        minute, hour, _, _, dow = parts
        sched.add_job(
            lambda p=podcast: intake.run_episode(db, p, _episode_anchor()),
            CronTrigger(minute=minute, hour=hour, day_of_week=dow, jitter=300),
            id=f"podcast:weekly:{podcast.project_slug}",
            misfire_grace_time=3600,
        )
        log.info("scheduled weekly podcast for %s at %s", podcast.project_slug, podcast.cron)

    sched.start()
    log.info("scheduler started with %d jobs", len(sched.get_jobs()))


def stop_jobs() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("scheduler stopped")


async def _synthesis_lead_pipeline(db: Database):
    await orchestrator.run_synthesis_lead(db)
    # Audio before publish so the snapshot includes the lead URL on the
    # first write. Audio failure must not block publish — readers still
    # need the text brief even if TTS is broken.
    try:
        await orchestrator.run_audio(db, kind="lead")
    except Exception as exc:
        log.warning("audio:lead failed; publishing without audio: %s", exc)
    await orchestrator.run_publish(db)


def _episode_anchor() -> date:
    """Start date for the weekly podcast's coverage window.

    Anchored at "trailing 7 days" rather than the previous calendar week
    (Mon→Sun) so the cron's firing day can move without leaving a
    multi-day reporting gap. With the default compose_window_days=7,
    a Saturday run covers last Sat→Fri.
    """
    return date.today() - timedelta(days=7)


async def _from_the_desk_weekly(db: Database) -> None:
    """Run synthesis:from_the_desk for every active+held project."""
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT slug, display_name FROM projects WHERE status IN ('active','held')"
        )
        project_rows = await cur.fetchall()
    for slug, display_name in project_rows:
        async with db.cursor() as cur:
            await cur.execute(
                "SELECT kind, title, occurred_at FROM events "
                "WHERE project_slug = ? AND occurred_at >= date('now', '-7 days') "
                "ORDER BY occurred_at",
                (slug,),
            )
            events = [
                {"kind": row[0], "title": row[1], "occurred_at": row[2]}
                for row in await cur.fetchall()
            ]
        result = await generate_from_the_desk(
            project_slug=slug, display_name=display_name, events=events
        )
        async with db.cursor() as cur:
            await cur.execute(
                "UPDATE projects SET from_the_desk = ?, from_the_desk_generated_at = ? WHERE slug = ?",
                (result["body"], result["generated_at"], slug),
            )
        log.info("from_the_desk[%s]: %s", slug, result["body"][:80])


async def _housekeeping(db: Database) -> None:
    """Rotate old runs, clean stale audio, vacuum weekly."""
    async with db.cursor() as cur:
        await cur.execute(
            "DELETE FROM runs WHERE started_at < date('now', '-30 days')"
        )
    await _cleanup_audio()
    log.info("housekeeping done")


async def _cleanup_audio() -> None:
    """Delete daily brief audio older than 7 days from R2."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    try:
        result = await list_objects(prefix="dispatch/audio/", limit=1000)
    except Exception as exc:
        log.warning("audio cleanup: failed to list objects: %s", exc)
        return

    objects = result.get("objects", [])
    deleted = 0
    for obj in objects:
        uploaded_str = obj.get("uploaded", "")
        if not uploaded_str:
            continue
        try:
            # Cloudflare returns ISO-8601 with Z suffix, e.g. 2026-05-01T00:00:00.000Z
            uploaded = datetime.fromisoformat(uploaded_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        if uploaded < cutoff:
            key = obj["name"]
            try:
                await delete_object(key)
                deleted += 1
            except Exception as exc:
                log.warning("audio cleanup: failed to delete %s: %s", key, exc)
    if deleted:
        log.info("audio cleanup: deleted %d stale audio file(s)", deleted)
