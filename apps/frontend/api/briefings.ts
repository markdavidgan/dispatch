import type { VercelRequest, VercelResponse } from "@vercel/node";
import { getDb } from "./_lib/db";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "GET") return res.status(405).end();
  const limit = Math.min(200, Math.max(1, parseInt(req.query.limit as string) || 50));
  const offset = Math.max(0, parseInt(req.query.offset as string) || 0);
  const db = getDb();

  const rows = await db.execute({
    sql: "SELECT date, issue_no, lead_headline, active_count, generated_at FROM filings WHERE kind='lead' ORDER BY date DESC LIMIT ? OFFSET ?",
    args: [limit, offset],
  });
  const totalRow = await db.execute({
    sql: "SELECT COUNT(*) FROM filings WHERE kind='lead'",
    args: [],
  });

  const base = process.env.R2_PUBLIC_BASE_URL?.replace(/\/$/, "") || "";
  const briefings = rows.rows.map((r) => ({
    date: r.date,
    issue_no: r.issue_no,
    lead_headline: r.lead_headline || "",
    audio_url: base ? `${base}/dispatch/audio/${r.date}-lead.wav` : null,
    active_count: r.active_count || 0,
    filed_at: r.generated_at ? (r.generated_at as string).split("T")[1].slice(0, 5) : "",
  }));

  res.status(200).json({ briefings, total: totalRow.rows[0]?.[0] || 0 });
}
