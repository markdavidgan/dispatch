import type { VercelRequest, VercelResponse } from "@vercel/node";
import { getDb } from "../../_lib/db.js";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "GET") return res.status(405).end();
  const db = getDb();
  const limit = Math.min(200, Math.max(1, parseInt(req.query.limit as string) || 50));
  const offset = Math.max(0, parseInt(req.query.offset as string) || 0);
  const job = (req.query.job as string) || "";
  const status = (req.query.status as string) || "";

  let sql = "SELECT id, job, status, started_at, finished_at, events_added, error FROM runs WHERE 1=1";
  const args: any[] = [];
  if (job) { sql += " AND job = ?"; args.push(job); }
  if (status) { sql += " AND status = ?"; args.push(status); }
  sql += " ORDER BY started_at DESC LIMIT ? OFFSET ?";
  args.push(limit, offset);

  const rows = await db.execute({ sql, args });
  const totalRow = await db.execute({ sql: "SELECT COUNT(*) FROM runs", args: [] });

  res.status(200).json({
    runs: rows.rows.map((r) => ({
      id: r.id,
      job: r.job,
      status: r.status,
      started_at: r.started_at,
      finished_at: r.finished_at,
      events_added: r.events_added,
      error: r.error,
    })),
    total: totalRow.rows[0]?.[0] || 0,
  });
}
