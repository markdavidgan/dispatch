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
    """Returns configuration status for the setup wizard."""
    store = request.app.state.settings_store
    db = request.app.state.db

    # Check if storage is configured
    storage_provider = await store.get("storage.provider", "")
    has_storage = bool(storage_provider)

    # Check AI provider
    ai_provider = await store.get("ai.provider", "")
    has_ai = bool(ai_provider)

    # Check TTS
    tts_provider = await store.get("tts.provider", "")
    has_tts = bool(tts_provider)

    # Check GitHub token
    gh_token = await store.get("github.global_token", "")
    has_github = bool(gh_token)

    # Check projects
    async with db.cursor() as cur:
        await cur.execute("SELECT COUNT(*) FROM projects")
        row = await cur.fetchone()
    has_projects = (row[0] or 0) > 0

    settings = get_settings()
    return {
        "storage": has_storage,
        "ai": has_ai,
        "tts": has_tts,
        "github_token_present": has_github,
        "project_count": row[0] or 0,
        "storage_provider": storage_provider or None,
        "ai_provider": ai_provider or None,
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
    max_days: int = 30
    ingest: bool = True


@router.post("/backfill")
async def backfill(request: Request, body: BackfillBody | None = None) -> dict[str, Any]:
    """Catch-up backfill: ingest fresh events, then synthesize one brief per
    uncovered day with activity until the look-back window is fully covered
    (capped at *max_days* iterations).

    Used by `scripts/bootstrap.sh` on first boot and available as a
    one-shot admin action whenever the instance falls behind.
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

    generated: list[str] = []
    errors: list[str] = []
    for _ in range(max(1, body.max_days)):
        try:
            result = await orchestrator.run_synthesis_lead(db)
        except Exception as e:
            log.exception("backfill synthesis failed")
            errors.append(str(e)[:500])
            break
        if result.get("skipped"):
            break
        if result.get("date"):
            generated.append(result["date"])

    return {
        "ingested": ingested,
        "generated": generated,
        "errors": errors,
    }
