"""Health endpoints. /health is public; others land in Task 1.4 behind CF Access."""
from fastapi import APIRouter, Request
from datetime import datetime, timezone

router = APIRouter()


@router.get("/health")
async def health(request: Request) -> dict:
    return {
        "status": "healthy",
        "service": "dispatch-collector",
        "version": "0.1.0",
        "ts": datetime.now(timezone.utc).isoformat(),
        "db_ok": request.app.state.db._conn is not None,
    }
