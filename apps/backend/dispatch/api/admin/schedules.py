"""Admin schedules API — view and edit job schedules."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/admin/schedules")


class ScheduleUpdate(BaseModel):
    cron_expression: str | None = None
    is_enabled: bool | None = None


@router.get("")
async def list_schedules(request: Request) -> list[dict[str, Any]]:
    db = request.app.state.db
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT job_name, cron_expression, is_enabled, last_run_at, next_run_at FROM schedules ORDER BY job_name"
        )
        rows = await cur.fetchall()
    return [
        {
            "job_name": r[0],
            "cron_expression": r[1],
            "is_enabled": bool(r[2]),
            "last_run_at": r[3],
            "next_run_at": r[4],
        }
        for r in rows
    ]


@router.get("/{job_name}")
async def get_schedule(request: Request, job_name: str) -> dict[str, Any]:
    db = request.app.state.db
    async with db.cursor() as cur:
        await cur.execute(
            "SELECT job_name, cron_expression, is_enabled, last_run_at, next_run_at FROM schedules WHERE job_name = ?",
            (job_name,),
        )
        row = await cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {
        "job_name": row[0],
        "cron_expression": row[1],
        "is_enabled": bool(row[2]),
        "last_run_at": row[3],
        "next_run_at": row[4],
    }


@router.patch("/{job_name}")
async def update_schedule(request: Request, job_name: str, body: ScheduleUpdate) -> dict[str, Any]:
    db = request.app.state.db
    fields = []
    params: list[Any] = []
    if body.cron_expression is not None:
        fields.append("cron_expression = ?")
        params.append(body.cron_expression)
    if body.is_enabled is not None:
        fields.append("is_enabled = ?")
        params.append(1 if body.is_enabled else 0)
    if not fields:
        return await get_schedule(request, job_name)
    params.append(job_name)
    async with db.cursor() as cur:
        await cur.execute(
            f"UPDATE schedules SET {', '.join(fields)} WHERE job_name = ?",
            params,
        )
    return await get_schedule(request, job_name)
