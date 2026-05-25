"""Admin briefing generation — manual trigger.

The single "Generate Briefing" button:
  1. Finds the latest uncovered day with activity (look-back window: 30 days).
  2. If found, synthesizes a lead for that day + audio + publishes.
  3. If no uncovered active day, returns a no-op response.

There is intentionally no "catch up the whole backlog" behavior — the daily
scheduler covers yesterday-if-active and that is the only catch-up path. Use
`POST /api/admin/system/backfill` (also single-day) for first-install priming.

Idempotent at the DB layer: re-running on a date that already has a lead
returns success without burning LLM credits.

Addendum support (refreshing today's brief with intra-day activity) lives at
`POST /api/brief/refresh` and is unaffected by this endpoint.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Request, HTTPException

from core.db import Database
from dispatch import orchestrator

router = APIRouter(prefix="/admin/briefings")
log = logging.getLogger(__name__)

_GENERATION_TIMEOUT = 60.0
_lock = asyncio.Lock()


@router.post("/generate")
async def generate_briefing(request: Request) -> dict:
    """Generate the next briefing that should be written."""
    db: Database = request.app.state.db

    async with _lock:
        target = await orchestrator.find_latest_uncovered_day_with_activity(db)
        if target is None:
            return {
                "generated": False,
                "reason": "no uncovered day with activity in the last 30 days",
            }

        log.info("manual generate: targeting %s (latest uncovered active day)", target)
        try:
            lead = await asyncio.wait_for(
                orchestrator.run_synthesis_lead(db, target_date=target),
                timeout=_GENERATION_TIMEOUT,
            )
        except Exception as e:
            log.exception("lead synthesis failed")
            raise HTTPException(503, detail=f"Lead synthesis failed: {e}")

        if lead.get("skipped"):
            return {
                "generated": False,
                "date": target.isoformat(),
                "reason": lead.get("reason", "no events"),
            }

        audio = None
        try:
            audio = await asyncio.wait_for(
                orchestrator.run_audio(db, kind="lead", target_date=lead["date"]),
                timeout=_GENERATION_TIMEOUT,
            )
        except Exception as e:
            log.warning("audio non-fatal failure: %s", e)

        try:
            url, _snapshot = await asyncio.wait_for(
                orchestrator.run_publish(db), timeout=_GENERATION_TIMEOUT
            )
        except Exception as e:
            log.exception("publish failed")
            raise HTTPException(503, detail=f"Publish failed: {e}")

        return {
            "generated": True,
            "kind": "lead",
            "date": lead["date"],
            "issue_no": lead.get("issue_no"),
            "headline": lead.get("headline"),
            "snapshot_url": url,
            "audio": audio,
        }
