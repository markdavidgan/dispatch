"""Project listing endpoint.

Protected by the deployment perimeter (e.g. Cloudflare Access, Tailscale,
reverse-proxy basic auth). No app-layer authentication. See CLAUDE.md.
"""
from fastapi import APIRouter, Request

from core.db import Database

router = APIRouter(prefix="/projects")


@router.get("")
async def list_projects(request: Request) -> list[dict]:
    db: Database = request.app.state.db
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT slug, display_name, status, kind, color_hint, github_repo, local_path FROM projects ORDER BY status DESC, slug"
        )
        rows = await cur.fetchall()
    return [
        {
            "slug": r[0],
            "display_name": r[1],
            "status": r[2],
            "kind": r[3],
            "color_hint": r[4],
            "github_repo": r[5],
            "local_path": r[6],
        }
        for r in rows
    ]
