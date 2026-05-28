"""Proxy routes — mirror the Vercel frontend serverless proxies so that
local development (Vite dev server → backend) works without the SPA
needing to know which environment it is in."""
from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/proxy")


@router.get("/setup-status")
async def proxy_setup_status(request: Request):
    """Delegate to the admin system setup-status endpoint."""
    from dispatch.api.admin.system import setup_status

    return await setup_status(request)


@router.api_route("/podcasts", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_podcasts(request: Request):
    """Forward podcast requests to the backend podcast router.

    The frontend sends ?path=/slug/episodes; we map that to the internal
    podcast router paths.
    """
    path = (request.query_params.get("path") or "").lstrip("/")

    from dispatch.api.podcast import list_podcasts, episodes

    if path == "":
        return await list_podcasts(request)

    parts = path.split("/")
    if len(parts) == 2 and parts[1] == "episodes":
        return await episodes(parts[0], request)

    raise HTTPException(404, detail=f"Unsupported podcast proxy path: {path}")
