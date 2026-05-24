"""Admin runs API — view job execution history."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Query

router = APIRouter(prefix="/admin/runs")


@router.get("")
async def list_runs(
    request: Request,
    job_name: str = Query(""),
    status: str = Query(""),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    db = request.app.state.db
    conditions = ["1=1"]
    params: list[Any] = []
    if job_name:
        conditions.append("job = ?")
        params.append(job_name)
    if status:
        conditions.append("status = ?")
        params.append(status)

    where_clause = " AND ".join(conditions)
    count_params = list(params)
    params.extend([limit, offset])

    async with db.cursor() as cur:
        await cur.execute(
            f"SELECT COUNT(*) FROM runs WHERE {where_clause}",
            count_params,
        )
        total_row = await cur.fetchone()
        total = total_row[0] if total_row else 0

        await cur.execute(
            f"""SELECT id, job, status, started_at, finished_at, events_added, error
                FROM runs WHERE {where_clause}
                ORDER BY started_at DESC
                LIMIT ? OFFSET ?""",
            params,
        )
        rows = await cur.fetchall()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "runs": [
            {
                "id": r[0],
                "job_name": r[1],
                "status": r[2],
                "started_at": r[3],
                "finished_at": r[4],
                "events_added": r[5],
                "error": r[6],
            }
            for r in rows
        ],
    }
