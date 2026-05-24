"""Admin briefing generation — manual trigger for lead or addendum.

Idempotent at the DB layer (ON CONFLICT DO UPDATE). A simple in-memory
lock prevents concurrent generation from burning duplicate LLM credits.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Request, HTTPException

from core.config import get_settings
from core.db import Database
from dispatch import orchestrator

router = APIRouter(prefix="/admin/briefings")
log = logging.getLogger(__name__)

_GENERATION_TIMEOUT = 60.0
_lock = asyncio.Lock()


@router.post("/generate")
async def generate_briefing(request: Request) -> dict:
    """Generate the latest briefing.

    If no lead exists for the target date (yesterday in dispatch tz),
    synthesize a lead. If a lead already exists, synthesize a rolling
    addendum for today. Then audio + publish.

    Idempotent: re-running on the same day updates the existing row
    via ON CONFLICT (date, kind) DO UPDATE.
    """
    db: Database = request.app.state.db

    # Determine target date (yesterday in dispatch tz)
    tz = get_settings().dispatch_tz
    now = datetime.now(timezone.utc)
    # Use the same "yesterday" logic as the scheduler
    target_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    async with _lock:
        # Check if lead already exists for target date
        async with db.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM filings WHERE date = ? AND kind = 'lead'",
                (target_date,),
            )
            has_lead = await cur.fetchone() is not None

        if has_lead:
            # Generate addendum
            log.info("manual generate: lead exists for %s; generating addendum", target_date)
            try:
                addendum = await asyncio.wait_for(
                    orchestrator.run_synthesis_addendum(db), timeout=_GENERATION_TIMEOUT
                )
            except Exception as e:
                log.exception("addendum generation failed")
                raise HTTPException(503, detail=f"Addendum generation failed: {e}")

            text = f"{addendum['label']}. {addendum['body']}"
            audio = None
            try:
                audio = await asyncio.wait_for(
                    orchestrator.run_audio(db, text=text, kind="addendum"),
                    timeout=_GENERATION_TIMEOUT,
                )
            except Exception:
                pass  # audio is non-fatal

            try:
                url, snapshot = await asyncio.wait_for(
                    orchestrator.run_publish(db), timeout=_GENERATION_TIMEOUT
                )
            except Exception as e:
                log.exception("publish failed")
                raise HTTPException(503, detail=f"Publish failed: {e}")

            return {
                "generated": True,
                "kind": "addendum",
                "date": addendum["date"],
                "label": addendum["label"],
                "snapshot_url": url,
                "audio": audio,
            }

        else:
            # Generate lead
            log.info("manual generate: no lead for %s; synthesizing lead", target_date)
            try:
                lead = await asyncio.wait_for(
                    orchestrator.run_synthesis_lead(db), timeout=_GENERATION_TIMEOUT
                )
            except Exception as e:
                log.exception("lead synthesis failed")
                raise HTTPException(503, detail=f"Lead synthesis failed: {e}")

            if lead.get("skipped"):
                return {
                    "generated": False,
                    "kind": "lead",
                    "date": target_date,
                    "reason": lead.get("reason", "no events"),
                }

            try:
                audio = await asyncio.wait_for(
                    orchestrator.run_audio(db, kind="lead"),
                    timeout=_GENERATION_TIMEOUT,
                )
            except Exception:
                pass  # audio is non-fatal

            try:
                url, snapshot = await asyncio.wait_for(
                    orchestrator.run_publish(db), timeout=_GENERATION_TIMEOUT
                )
            except Exception as e:
                log.exception("publish failed")
                raise HTTPException(503, detail=f"Publish failed: {e}")

            return {
                "generated": True,
                "kind": "lead",
                "date": lead["date"],
                "issue_no": lead["issue_no"],
                "headline": lead["headline"],
                "snapshot_url": url,
                "audio": audio,
            }
