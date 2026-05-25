"""Snapshot assembly, signing, and publishing.

The snapshot is the JSON contract consumed by the frontend SPA.
It is HMAC-signed so the frontend can verify integrity before rendering.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone

from core.db import Database
from dispatch.publish.r2 import upload_bytes

log = logging.getLogger(__name__)

SNAPSHOT_KEY = "dispatch/snapshot.json"
ARCHIVE_PREFIX = "dispatch/snapshot-archive"
SIGNING_SECRET_ENV = "DISPATCH_SNAPSHOT_SECRET"


def _public_audio_url(url: str | None) -> str | None:
    """Translate a stored audio URL into a browser-loadable HTTP URL.

    Local-filesystem storage records URLs as `local://<key>` placeholders.
    Without translation those URLs can't be loaded by the SPA. When
    R2_PUBLIC_BASE_URL is set, prefix it; otherwise return the URL as-is
    (R2/S3 URLs are already public).
    """
    if not url:
        return None
    if not url.startswith("local://"):
        return url
    base = os.environ.get("R2_PUBLIC_BASE_URL", "").rstrip("/")
    if not base:
        return None
    return f"{base}/{url[len('local://'):]}"


def _signing_secret() -> bytes:
    secret = os.environ.get(SIGNING_SECRET_ENV, "")
    if not secret:
        # deterministic fallback for local dev; rotate in prod
        secret = "dispatch-dev-secret-rotate-me"
    return secret.encode()


def _sign_payload(payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    sig = hmac.new(_signing_secret(), body.encode(), hashlib.sha256).hexdigest()[:32]
    return sig


async def build_snapshot(db: Database) -> dict:
    """Assemble the current snapshot from DB state."""
    now = datetime.now(timezone.utc).isoformat()

    # Projects
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT slug, display_name, status, kind, color_hint, from_the_desk, from_the_desk_generated_at FROM projects ORDER BY status DESC, slug"
        )
        project_rows = await cur.fetchall()

    projects: list[dict] = []
    for row in project_rows:
        slug = row[0]
        project_payload = {
            "slug": slug,
            "name": row[1],
            "status": row[2],
            "kind": row[3],
            "color_hint": row[4],
            "from_the_desk": row[5],
            "from_the_desk_generated_at": row[6],
        }
        # N+1 by design: project count is bounded (~10) and the
        # `briefing_mentions_project` index (project_slug, briefing_date DESC)
        # makes each lookup O(log n). At this scale a single batched query
        # with window-function ranking would be more code with no perf win.
        async with db.cursor() as cur:
            await cur.execute(
                "SELECT briefing_date, excerpt FROM briefing_mentions "
                "WHERE project_slug = ? "
                "ORDER BY briefing_date DESC, position ASC LIMIT 5",
                (slug,),
            )
            mention_rows = await cur.fetchall()
        project_payload["mentioned_in_briefings"] = [
            {"date": m_row[0], "excerpt": m_row[1]} for m_row in mention_rows
        ]
        projects.append(project_payload)

    # Latest brief (most recent lead filing)
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT date FROM filings WHERE kind='lead' ORDER BY date DESC LIMIT 1"
        )
        latest_row = await cur.fetchone()
    latest_date = latest_row[0] if latest_row else None

    async with db.cursor() as cur:
        if latest_date:
            await cur.execute(
                "SELECT date, kind, issue_no, covers_from, covers_until, lead_headline, lead_body, active_count, project_lines, addendum_label, addendum_body, model, generated_at, audio_url, audio_duration_s FROM filings WHERE date=? ORDER BY kind, id",
                (latest_date,),
            )
        else:
            await cur.execute(
                "SELECT date, kind, issue_no, covers_from, covers_until, lead_headline, lead_body, active_count, project_lines, addendum_label, addendum_body, model, generated_at, audio_url, audio_duration_s FROM filings WHERE 1=0"
            )
        rows = await cur.fetchall()

    from dispatch.scheduler import get_lead_time
    lead_time = await get_lead_time(db)

    lead: dict | None = None
    addendums: list[dict] = []
    lead_audio_url: str | None = None
    lead_audio_dur: int | None = None
    addendum_audio_url: str | None = None
    addendum_audio_dur: int | None = None
    for row in rows:
        (
            date, kind, issue_no, covers_from, covers_until,
            lead_headline, lead_body, active_count, project_lines_json,
            addendum_label, addendum_body, model, generated_at,
            audio_url, audio_duration_s,
        ) = row
        if kind == "lead":
            projects_in_brief = json.loads(project_lines_json or "[]")
            lead = {
                "date": date,
                "issue_no": issue_no,
                "filed_at": generated_at.split("T")[1][:5] if generated_at and "T" in generated_at else lead_time,
                "active_count": f"{active_count:02d}" if active_count is not None else "00",
                "lead_headline": lead_headline or "",
                "lead_body": lead_body or "",
                "projects": projects_in_brief,
                "addendums": [],  # filled below
                "audio": None,    # filled below
            }
            lead_audio_url = audio_url
            lead_audio_dur = audio_duration_s
        elif kind == "addendum":
            addendums.append({
                "filed_at": generated_at.split("T")[1][:5] if generated_at and "T" in generated_at else "",
                "label": addendum_label or f"Filed since {lead_time}",
                "body": addendum_body or "",
            })
            # Latest addendum wins — rows are ordered by id ascending within
            # this kind, so the last non-null URL we see is the freshest.
            if audio_url:
                addendum_audio_url = audio_url
                addendum_audio_dur = audio_duration_s

    if lead:
        lead["addendums"] = addendums
        public_lead = _public_audio_url(lead_audio_url)
        public_addendum = _public_audio_url(addendum_audio_url)
        if public_lead or public_addendum:
            lead["audio"] = {
                "lead_url": public_lead,
                "lead_duration_s": lead_audio_dur,
                "addendum_url": public_addendum,
                "addendum_duration_s": addendum_audio_dur,
                "voice": os.environ.get("GCP_TTS_VOICE", "en-US-Chirp3-HD-Leda"),
            }

    # Recent events (last 50)
    async with db.cursor() as cur:
        await cur.execute(
            """SELECT project_slug, kind, external_id, title, author, occurred_at, url
               FROM events ORDER BY occurred_at DESC LIMIT 50"""
        )
        recent_events = [
            {
                "project_slug": row[0],
                "kind": row[1],
                "external_id": row[2],
                "title": row[3],
                "author": row[4],
                "occurred_at": row[5],
                "url": row[6],
            }
            for row in await cur.fetchall()
        ]

    episodes: list[dict] = []

    payload = {
        "version": 1,
        "generated_at": now,
        "brief": lead,
        "projects": projects,
        "recent_events": recent_events,
        "episodes": episodes,
    }

    payload["signature"] = _sign_payload(payload)
    return payload


async def publish_snapshot(db: Database) -> tuple[str, dict]:
    """Build snapshot, upload to R2, archive copy. Returns (public_url, snapshot)."""
    snapshot = await build_snapshot(db)
    data = json.dumps(snapshot, ensure_ascii=False, indent=2).encode()

    # Main snapshot (overwritten)
    url = await upload_bytes(data, SNAPSHOT_KEY, "application/json")

    # Archive copy (immutable, dated)
    date_stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    archive_key = f"{ARCHIVE_PREFIX}/{date_stamp}.json"
    await upload_bytes(data, archive_key, "application/json")

    log.info("snapshot published: %s", url)
    return url, snapshot


def _normalize_snapshot(snapshot: dict) -> dict:
    """Translate historical snapshot field names to the post-rename shape.

    Plan 3 (2026-05-18) renamed `bureau_lines` → `project_lines` (filings
    column) and reshaped `brief.bureaus` → `brief.projects` in the snapshot
    JSON contract. Snapshots written before that date — including the
    archived copies in R2 at `dispatch/snapshot-archive/*.json` — still use
    the old field names. Any reader of those historical archives should
    push the dict through this shim first so downstream code can assume a
    single canonical shape.

    Idempotent — already-normalized snapshots pass through unchanged.
    Top-level (non-`brief`) keys are not rewritten; only fields known to
    have been renamed are touched.
    """
    if not isinstance(snapshot, dict):
        return snapshot
    brief = snapshot.get("brief")
    if isinstance(brief, dict) and "bureaus" in brief and "projects" not in brief:
        new_brief = {k: v for k, v in brief.items() if k != "bureaus"}
        new_brief["projects"] = brief["bureaus"]
        snapshot = {**snapshot, "brief": new_brief}
    return snapshot
