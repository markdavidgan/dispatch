import type { VercelRequest, VercelResponse } from "@vercel/node";
import { getDb, ensureSchema } from "../../_lib/db.js";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "PATCH") return res.status(405).end();
  const jobName = req.query.jobName as string;
  const body = req.body || {};
  const db = getDb();
  await ensureSchema(db);

  const sets: string[] = [];
  const args: any[] = [];
  if (body.cron_expression !== undefined) { sets.push("cron_expression = ?"); args.push(body.cron_expression); }
  if (body.timezone !== undefined) { sets.push("timezone = ?"); args.push(body.timezone); }
  if (body.is_enabled !== undefined) { sets.push("is_enabled = ?"); args.push(body.is_enabled ? 1 : 0); }

  if (!sets.length) return res.status(400).json({ error: "no fields to update" });

  args.push(jobName);
  await db.execute({
    sql: `UPDATE schedules SET ${sets.join(", ")} WHERE job_name = ?`,
    args,
  });
  res.status(200).json({ ok: true });
}
