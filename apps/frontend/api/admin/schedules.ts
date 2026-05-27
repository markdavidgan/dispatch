import type { VercelRequest, VercelResponse } from "@vercel/node";
import { getDb } from "../_lib/db.js";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "GET") return res.status(405).end();
  const db = getDb();
  const rows = await db.execute({
    sql: "SELECT job_name, cron_expression, timezone, is_enabled, last_run_at, next_run_at FROM schedules ORDER BY job_name",
    args: [],
  });
  res.status(200).json({
    schedules: rows.rows.map((r) => ({
      job_name: r.job_name,
      cron_expression: r.cron_expression,
      timezone: r.timezone,
      is_enabled: Boolean(r.is_enabled),
      last_run_at: r.last_run_at,
      next_run_at: r.next_run_at,
    })),
  });
}
