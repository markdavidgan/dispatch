"""Public snapshot API — serves the signed JSON snapshot directly."""
from __future__ import annotations

from fastapi import APIRouter, Request

from dispatch.publish.snapshot import build_snapshot

router = APIRouter(prefix="/snapshot")


@router.get("")
async def get_snapshot(request: Request) -> dict:
    db = request.app.state.db
    return await build_snapshot(db)
