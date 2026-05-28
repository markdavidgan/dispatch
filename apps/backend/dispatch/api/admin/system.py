"""System admin API — setup status, key rotation, backup trigger."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from core.config import get_settings

router = APIRouter(prefix="/admin/system")
log = logging.getLogger(__name__)


class RotateKeyBody(BaseModel):
    old_key: str
    new_key: str


@router.get("/setup-status")
async def setup_status(request: Request) -> dict[str, Any]:
    """Returns configuration status for the setup wizard + admin sidebar.

    Each capability flag is True when *either* a relevant setting is stored
    in the encrypted DB store, or the equivalent environment variable is
    present at boot. This keeps env-only installs (the common all-in-one
    Docker case) from looking misconfigured in the UI.
    """
    import os
    store = request.app.state.settings_store
    db = request.app.state.db

    storage_provider = await store.get("storage.provider", "")
    # Local filesystem is the implicit default at boot — count it as configured.
    has_storage = bool(storage_provider) or True

    ai_provider = await store.get("ai.provider", "")
    has_ai = bool(ai_provider) or bool(
        os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("KIMI_OAUTH_JSON")
        or os.environ.get("OPENAI_API_KEY")
    )

    tts_provider = await store.get("tts.provider", "")
    has_tts = bool(tts_provider) or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

    gh_token = await store.get("github.global_token", "")
    has_github = bool(gh_token) or bool(os.environ.get("GITHUB_TOKEN"))

    nblm = await store.get("podcast.notebooklm_session", "")
    has_notebooklm = bool(nblm)

    async with db.cursor() as cur:
        await cur.execute("SELECT COUNT(*) FROM projects WHERE kind != 'meta'")
        row = await cur.fetchone()

    settings = get_settings()
    return {
        "storage": has_storage,
        "ai": has_ai,
        "tts": has_tts,
        "github_token_present": has_github,
        "notebooklm": has_notebooklm,
        "project_count": row[0] or 0,
        "storage_provider": storage_provider or "local",
        "ai_provider": ai_provider or None,
        "tts_provider": tts_provider or None,
        "dispatch_tz": settings.dispatch_tz,
    }


@router.post("/rotate-key")
async def rotate_key(request: Request, body: RotateKeyBody) -> dict[str, Any]:
    """Re-encrypt all settings with a new master key."""
    from dispatch.crypto import Crypto

    db = request.app.state.db
    old_crypto = Crypto(body.old_key)
    new_crypto = Crypto(body.new_key)

    async with db.cursor() as cur:
        await cur.execute("SELECT key, value FROM settings")
        rows = await cur.fetchall()

    rotated = 0
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    for key, encrypted in rows:
        try:
            plaintext = old_crypto.decrypt(encrypted)
            new_encrypted = new_crypto.encrypt(plaintext)
        except Exception as e:
            log.warning("rotate-key: failed to decrypt %s: %s", key, e)
            continue
        async with db.cursor() as cur:
            await cur.execute(
                "UPDATE settings SET value = ?, updated_at = ? WHERE key = ?",
                (new_encrypted, now, key),
            )
        rotated += 1

    # Update canary
    from dispatch.system.key_canary import CANARY_PLAINTEXT
    new_canary = new_crypto.encrypt(CANARY_PLAINTEXT)
    async with db.cursor() as cur:
        await cur.execute(
            "UPDATE system SET value = ?, updated_at = ? WHERE key = 'key_canary'",
            (new_canary, now),
        )

    return {"rotated": rotated, "total": len(rows)}


@router.post("/backup-now")
async def backup_now(request: Request) -> dict[str, Any]:
    """Trigger an immediate SQLite backup."""
    from dispatch.system.backup import run_backup

    db = request.app.state.db
    store = request.app.state.settings_store
    try:
        result = await run_backup(db, store)
        return {"status": "ok", "result": result}
    except Exception as e:
        log.exception("backup failed")
        return {"status": "error", "error": str(e)}


class BackfillBody(BaseModel):
    look_back_days: int = 30
    ingest: bool = True


@router.post("/backfill")
async def backfill(request: Request, body: BackfillBody | None = None) -> dict[str, Any]:
    """First-install backfill: ingest fresh events, then synthesize a brief
    for the **latest** uncovered day with activity (one brief, single 24-hour
    window — not a multi-day catch-up).

    Used by `scripts/bootstrap.sh` on first boot. Quiet days are intentionally
    skipped — a brand-new instance with no recent activity reports nothing.
    """
    from dispatch import orchestrator

    body = body or BackfillBody()
    db = request.app.state.db

    ingested: dict[str, int | str] = {}
    if body.ingest:
        for name, fn in (
            ("github", orchestrator.run_ingest_github),
            ("git", orchestrator.run_ingest_git),
        ):
            try:
                ingested[name] = await fn(db)
            except Exception as e:
                log.warning("backfill ingest_%s failed: %s", name, e)
                ingested[name] = f"error: {e}"

    target = await orchestrator.find_latest_uncovered_day_with_activity(
        db, look_back_days=body.look_back_days
    )
    if target is None:
        return {
            "ingested": ingested,
            "generated": None,
            "reason": "no uncovered day with activity in look-back window",
        }

    try:
        result = await orchestrator.run_synthesis_lead(db, target_date=target)
    except Exception as e:
        log.exception("backfill synthesis failed")
        return {"ingested": ingested, "generated": None, "error": str(e)[:500]}

    # Non-fatal: try audio + publish so the brief is fully presentable.
    audio: dict | None = None
    try:
        audio = await orchestrator.run_audio(
            db, kind="lead", target_date=result.get("date")
        )
    except Exception as e:
        log.warning("backfill audio non-fatal failure: %s", e)
    try:
        await orchestrator.run_publish(db)
    except Exception as e:
        log.warning("backfill publish non-fatal failure: %s", e)

    return {
        "ingested": ingested,
        "generated": result.get("date"),
        "headline": result.get("headline"),
        "skipped": result.get("skipped", False),
        "reason": result.get("reason"),
        "audio": audio,
    }
