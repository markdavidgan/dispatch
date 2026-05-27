import type { VercelRequest, VercelResponse } from "@vercel/node";
import { getDb, ensureSchema } from "./_lib/db.js";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "GET") return res.status(405).end();
  const db = getDb();
  await ensureSchema(db);

  // Count commits in last 7 days
  const since = new Date();
  since.setDate(since.getDate() - 7);
  const commitRow = await db.execute({
    sql: "SELECT COUNT(*) FROM events WHERE kind='commit' AND occurred_at >= ?",
    args: [since.toISOString()],
  });

  // Count open PRs
  const prRow = await db.execute({
    sql: "SELECT COUNT(*) FROM events WHERE kind='pr_opened' AND occurred_at >= ?",
    args: [since.toISOString()],
  });

  // Last commit timestamp
  const lastRow = await db.execute({
    sql: "SELECT occurred_at FROM events WHERE kind='commit' ORDER BY occurred_at DESC LIMIT 1",
    args: [],
  });

  res.status(200).json({
    commits_7d: commitRow.rows[0]?.[0] || 0,
    prs_open_7d: prRow.rows[0]?.[0] || 0,
    last_commit_at: lastRow.rows[0]?.occurred_at || null,
  });
}
