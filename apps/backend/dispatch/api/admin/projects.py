"""Admin project registry CRUD API."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/admin/projects")


class ProjectCreate(BaseModel):
    slug: str
    display_name: str
    github_repo: str = ""
    status: str = "active"
    kind: str = "app"
    color_hint: str = ""
    summary: str = ""
    podcast_config: dict[str, Any] | None = None


class ProjectUpdate(BaseModel):
    display_name: str | None = None
    github_repo: str | None = None
    status: str | None = None
    kind: str | None = None
    color_hint: str | None = None
    summary: str | None = None
    podcast_config: dict[str, Any] | None = None


@router.get("")
async def list_projects(request: Request) -> list[dict[str, Any]]:
    db = request.app.state.db
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT slug, display_name, github_repo, status, kind, color_hint, summary, podcast_config, sort_order, created_at "
            "FROM projects ORDER BY sort_order, slug"
        )
        rows = await cur.fetchall()
    import json
    return [
        {
            "slug": r[0],
            "display_name": r[1],
            "github_repo": r[2],
            "status": r[3],
            "kind": r[4],
            "color_hint": r[5],
            "summary": r[6],
            "podcast_config": json.loads(r[7]) if r[7] else None,
            "sort_order": r[8],
            "created_at": r[9],
        }
        for r in rows
    ]


@router.post("")
async def create_project(request: Request, body: ProjectCreate) -> dict[str, Any]:
    db = request.app.state.db
    import json
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    async with db.cursor() as cur:
        await cur.execute(
            """INSERT INTO projects
               (slug, display_name, github_repo, status, kind, color_hint, summary, podcast_config, sort_order, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                body.slug, body.display_name, body.github_repo or None,
                body.status, body.kind, body.color_hint or None,
                body.summary or None,
                json.dumps(body.podcast_config) if body.podcast_config else None,
                0, now,
            ),
        )
    return {"slug": body.slug, "created": True}


@router.get("/{slug}")
async def get_project(request: Request, slug: str) -> dict[str, Any]:
    db = request.app.state.db
    import json
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT slug, display_name, github_repo, status, kind, color_hint, summary, podcast_config, sort_order, created_at "
            "FROM projects WHERE slug = ?",
            (slug,),
        )
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "slug": row[0],
        "display_name": row[1],
        "github_repo": row[2],
        "status": row[3],
        "kind": row[4],
        "color_hint": row[5],
        "summary": row[6],
        "podcast_config": json.loads(row[7]) if row[7] else None,
        "sort_order": row[8],
        "created_at": row[9],
    }


@router.patch("/{slug}")
async def update_project(request: Request, slug: str, body: ProjectUpdate) -> dict[str, Any]:
    db = request.app.state.db
    fields = []
    params: list[Any] = []
    import json
    if body.display_name is not None:
        fields.append("display_name = ?")
        params.append(body.display_name)
    if body.github_repo is not None:
        fields.append("github_repo = ?")
        params.append(body.github_repo or None)
    if body.status is not None:
        fields.append("status = ?")
        params.append(body.status)
    if body.kind is not None:
        fields.append("kind = ?")
        params.append(body.kind)
    if body.color_hint is not None:
        fields.append("color_hint = ?")
        params.append(body.color_hint or None)
    if body.summary is not None:
        fields.append("summary = ?")
        params.append(body.summary or None)
    if body.podcast_config is not None:
        fields.append("podcast_config = ?")
        params.append(json.dumps(body.podcast_config))
    if not fields:
        return await get_project(request, slug)
    params.append(slug)
    async with db.cursor() as cur:
        await cur.execute(
            f"UPDATE projects SET {', '.join(fields)} WHERE slug = ?",
            params,
        )
    return await get_project(request, slug)


@router.delete("/{slug}")
async def delete_project(request: Request, slug: str) -> dict[str, Any]:
    db = request.app.state.db
    async with db.cursor() as cur:
        await cur.execute("DELETE FROM projects WHERE slug = ?", (slug,))
    return {"slug": slug, "deleted": True}


@router.post("/reorder")
async def reorder_projects(request: Request, body: dict[str, list[str]]) -> dict[str, Any]:
    """Body: {"slugs": ["a", "b", "c"]} — sets sort_order accordingly."""
    db = request.app.state.db
    slugs = body.get("slugs", [])
    async with db.cursor() as cur:
        for i, slug in enumerate(slugs):
            await cur.execute(
                "UPDATE projects SET sort_order = ? WHERE slug = ?",
                (i, slug),
            )
    return {"reordered": len(slugs)}
