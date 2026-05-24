"""GET /briefings  — paginated list of past briefings.
GET /briefings/{date} — single archived briefing (full payload).

Both endpoints are perimeter-protected at the deployment layer
(Cloudflare Access, Tailscale, reverse-proxy auth — see CLAUDE.md).
"""
from __future__ import annotations

import json
import logging
import os

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from core.db import Database
from dispatch.publish.r2 import download_bytes

log = logging.getLogger(__name__)

router = APIRouter(prefix="/briefings")


def _audio_url(date: str, kind: str) -> str | None:
    """Deterministic R2 URL for a briefing's audio asset.

    Pattern: `{R2_PUBLIC_BASE_URL}/dispatch/audio/{date}-{kind}.mp3`
    Matches the upload key used by `orchestrator.run_audio()`. Returns
    None when R2_PUBLIC_BASE_URL isn't configured (e.g. local dev) so
    the frontend renders the no-audio state cleanly.

    Notes: the URL is constructed unconditionally — we don't HEAD-check
    the object. If audio generation failed for a given filing, the
    frontend's native `<audio>` element will silently fall back to its
    error state (no controls, no play). This matches the home page's
    behavior with `snapshot.brief.audio` URLs.
    """
    base = os.environ.get("R2_PUBLIC_BASE_URL", "").rstrip("/")
    if not base:
        return None
    return f"{base}/dispatch/audio/{date}-{kind}.mp3"


async def _recent_events_for_date(date: str) -> list[dict]:
    """Read recent_events from the R2 snapshot archive for `date`.

    Per spec §4.3: the events that fed a past briefing's synthesis are
    frozen in the snapshot archive at filing time. The `events` table
    itself is unified across all time; only the archive captures the
    slice the briefing summarized. Returns [] if the archive is missing
    or unreadable.
    """
    key = f"dispatch/snapshot-archive/{date}.json"
    try:
        data = await download_bytes(key)
    except Exception as exc:  # noqa: BLE001
        log.info("recent_events: no archive for %s (%s)", date, exc)
        return []
    try:
        snapshot = json.loads(data)
    except json.JSONDecodeError as exc:
        log.warning("recent_events: archive %s is malformed: %s", date, exc)
        return []
    return list(snapshot.get("recent_events") or [])


class BriefingSummary(BaseModel):
    date: str
    issue_no: int
    lead_headline: str
    audio_url: str | None = None
    active_count: int
    filed_at: str


class BriefingsList(BaseModel):
    briefings: list[BriefingSummary]
    total: int


class BriefingDetail(BaseModel):
    date: str
    issue_no: int
    lead_headline: str
    lead_body: str            # short dek shown on home/index
    lead_article: str = ""    # ~500-word long-form; what Ava reads aloud
    addendums: list[dict] = []
    projects: list[dict] = []
    audio_lead_url: str | None = None
    audio_addendum_url: str | None = None
    active_count: int
    filed_at: str
    recent_events: list[dict] = []


@router.get("", response_model=BriefingsList)
async def list_briefings(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> BriefingsList:
    db: Database = request.app.state.db
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT date, issue_no, lead_headline, active_count, generated_at "
            "FROM filings WHERE kind='lead' ORDER BY date DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cur.fetchall()
        await cur.execute("SELECT COUNT(*) FROM filings WHERE kind='lead'")
        (total,) = await cur.fetchone()

    from dispatch.scheduler import get_lead_time
    lead_time = await get_lead_time(db)
    briefings = [
        BriefingSummary(
            date=row[0],
            issue_no=row[1],
            lead_headline=row[2] or "",
            audio_url=_audio_url(row[0], "lead"),
            active_count=row[3] or 0,
            filed_at=(row[4] or "")[11:16] or lead_time,
        )
        for row in rows
    ]
    return BriefingsList(briefings=briefings, total=total)


@router.get("/{date}", response_model=BriefingDetail)
async def get_briefing(request: Request, date: str) -> BriefingDetail:
    db: Database = request.app.state.db
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT date, kind, issue_no, lead_headline, lead_body, "
            "active_count, project_lines, generated_at, addendum_label, addendum_body, "
            "lead_article "
            "FROM filings WHERE date = ? ORDER BY kind",
            (date,),
        )
        rows = await cur.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"no briefing filed for {date}")

    lead = next((r for r in rows if r[1] == "lead"), None)
    if not lead:
        raise HTTPException(status_code=404, detail=f"no lead filing for {date}")

    projects = json.loads(lead[6] or "[]")
    addendums = [
        {"filed_at": (r[7] or "")[11:16], "label": r[8] or "", "body": r[9] or ""}
        for r in rows if r[1] == "addendum"
    ]
    has_addendum = any(r[1] == "addendum" for r in rows)

    recent_events = await _recent_events_for_date(date)

    from dispatch.scheduler import get_lead_time
    lead_time = await get_lead_time(db)
    return BriefingDetail(
        date=lead[0],
        issue_no=lead[2] or 0,
        lead_headline=lead[3] or "",
        lead_body=lead[4] or "",
        lead_article=lead[10] or "",
        addendums=addendums,
        projects=projects,
        audio_lead_url=_audio_url(date, "lead"),
        audio_addendum_url=_audio_url(date, "addendum") if has_addendum else None,
        active_count=lead[5] or 0,
        filed_at=(lead[7] or "")[11:16] or lead_time,
        recent_events=recent_events,
    )
