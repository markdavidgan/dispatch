"""APScheduler wiring — ingest, synthesis, publish, audio, podcast, housekeeping.

All jobs run in-process. Jittered start avoids thundering herd.
Cron schedules are read from the DB at startup; interval jobs remain
hardcoded. A restart (or calling reload_job) is required for schedule
changes to take effect.
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
from dispatch.ingest import github_commits

log = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None
_db: Database | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=os.environ.get("DISPATCH_TZ", "Asia/Manila"))
    return _scheduler


def _jittered_minute() -> int:
    return random.randint(0, 59)


def _parse_cron(cron: str) -> dict:
    """Parse a 5-part cron string into CronTrigger kwargs."""
    parts = cron.split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {cron!r} (expected 5 parts)")
    minute, hour, day, month, dow = parts
    return {
        "minute": minute,
        "hour": hour,
        "day": day if day != "*" else None,
        "month": month if month != "*" else None,
        "day_of_week": dow if dow != "*" else None,
    }


async def _load_cron_schedules(db: Database) -> list[dict]:
    """Read cron schedules from the DB."""
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT job_name, cron_expression, timezone, is_enabled FROM schedules WHERE job_name != ''"
        )
        rows = await cur.fetchall()
    return [
        {"job_name": r[0], "cron": r[1], "timezone": r[2] or "UTC", "enabled": bool(r[3])}
        for r in rows
    ]


async def start_jobs(db: Database) -> None:
    global _db
    _db = db
    sched = get_scheduler()

    # Interval-based ingest jobs (not configurable via schedules table)
    sched.add_job(
        orchestrator.run_ingest_git,
        IntervalTrigger(minutes=15, jitter=60),
        args=[db],
        id="ingest_git",
        replace_existing=True,
    )
    sched.add_job(
        orchestrator.run_ingest_github,
        IntervalTrigger(minutes=30, jitter=60),
        args=[db],
        id="ingest_github",
        replace_existing=True,
    )
    sched.add_job(
        _ingest_github_commits,
        IntervalTrigger(minutes=60, jitter=120),
        args=[db],
        id="ingest_github_commits",
        replace_existing=True,
    )

    # Cron-based jobs from DB
    schedules = await _load_cron_schedules(db)
    for s in schedules:
        if not s["enabled"]:
            log.info("schedule %s is disabled; skipping", s["job_name"])
            continue
        _add_cron_job(sched, db, s["job_name"], s["cron"], s["timezone"])

    # Podcasts: one weekly job per enabled podcast (from projects.yml)
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


def _add_cron_job(sched: AsyncIOScheduler, db: Database, job_name: str, cron: str, tz: str) -> None:
    """Add or replace a cron job from the schedules table."""
    try:
        kwargs = _parse_cron(cron)
    except ValueError as e:
        log.warning("bad cron for %s: %s", job_name, e)
        return

    trigger = CronTrigger(**kwargs, timezone=tz)

    job_map = {
        "synthesis:lead": (_synthesis_lead_pipeline, [db]),
        "housekeeping": (_housekeeping, [db]),
        "synthesis:from_the_desk": (_from_the_desk_weekly, [db]),
    }

    if job_name not in job_map:
        log.warning("unknown cron job %s; skipping", job_name)
        return

    func, args = job_map[job_name]
    sched.add_job(func, trigger, args=args, id=job_name, replace_existing=True)
    log.info("scheduled %s at %s (%s)", job_name, cron, tz)


async def get_lead_time(db: Database) -> str:
    """Return the configured lead synthesis time as HH:MM from the schedules table."""
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT cron_expression FROM schedules WHERE job_name = 'synthesis:lead'"
        )
        row = await cur.fetchone()
    if row:
        parts = row[0].split()
        if len(parts) == 5:
            return f"{parts[1].zfill(2)}:{parts[0].zfill(2)}"
    return "01:00"


def reload_job(job_name: str, cron: str | None = None, timezone: str | None = None, enabled: bool = True) -> bool:
    """Reload a single cron job without restarting the whole scheduler.

    Returns True if the job was updated, False if the scheduler isn't running.
    """
    global _db
    if _scheduler is None or _db is None:
        return False
    sched = get_scheduler()

    if not enabled:
        try:
            sched.remove_job(job_name)
            log.info("removed job %s", job_name)
        except Exception:
            pass
        return True

    if cron is None:
        return False

    _add_cron_job(sched, _db, job_name, cron, timezone or "UTC")
    return True


def stop_jobs() -> None:
    global _scheduler, _db
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        _db = None
        log.info("scheduler stopped")


async def _ingest_github_commits(db: Database) -> None:
    """Run branch-aware commit ingest for all projects with a github_repo."""
    async with db.cursor() as cur:
        await cur.execute("SELECT slug, github_repo FROM projects WHERE github_repo IS NOT NULL")
        rows = await cur.fetchall()
    for slug, repo in rows:
        try:
            n = await github_commits.ingest_commits(db, slug, repo)
            if n:
                log.info("github commits: %s +%d", slug, n)
        except Exception as e:
            log.exception("github commits failed for %s", slug)


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
