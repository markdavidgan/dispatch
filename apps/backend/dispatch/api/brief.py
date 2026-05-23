"""Brief refresh endpoint — on-demand addendum synthesis + publish + audio.

Protected by the deployment perimeter (e.g. Cloudflare Access, Tailscale,
reverse-proxy basic auth). No app-layer authentication. See CLAUDE.md.
Synchronous response (~5-15s). Capped at 25s to avoid gateway timeouts.
"""
import asyncio

from fastapi import APIRouter, Request, HTTPException

from dispatch import orchestrator

router = APIRouter(prefix="/brief")

_REFRESH_TIMEOUT = 25.0


@router.post("/refresh")
async def refresh(request: Request) -> dict:
    db = request.app.state.db
    try:
        addendum = await asyncio.wait_for(
            orchestrator.run_synthesis_addendum(db), timeout=_REFRESH_TIMEOUT
        )
        # Audio before publish so the addendum URL is in the snapshot's
        # first write. Audio failure is non-fatal — text still ships.
        text = f"{addendum['label']}. {addendum['body']}"
        audio: dict | None = None
        try:
            audio = await asyncio.wait_for(
                orchestrator.run_audio(db, text=text, kind="addendum"),
                timeout=_REFRESH_TIMEOUT,
            )
        except Exception:
            audio = None
        url, snapshot = await asyncio.wait_for(
            orchestrator.run_publish(db), timeout=_REFRESH_TIMEOUT
        )
        return {
            "ok": True,
            "addendum": addendum,
            "snapshot_url": url,
            "audio": audio,
        }
    except asyncio.TimeoutError:
        raise HTTPException(504, detail="Refresh timed out — try again shortly")
    except Exception as e:
        raise HTTPException(503, detail=f"Refresh failed: {e}")
