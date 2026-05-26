import type { VercelRequest, VercelResponse } from "@vercel/node";
import { getDb } from "../../../_lib/db.js";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "GET") return res.status(405).end();
  const db = getDb();
  const projectCount = await db.execute({ sql: "SELECT COUNT(*) FROM projects", args: [] });
  const filingCount = await db.execute({ sql: "SELECT COUNT(*) FROM filings WHERE kind='lead'", args: [] });

  res.status(200).json({
    setup: {
      projects_count: projectCount.rows[0]?.[0] || 0,
      filings_count: filingCount.rows[0]?.[0] || 0,
    },
  });
}
