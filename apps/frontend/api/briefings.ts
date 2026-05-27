import type { VercelRequest, VercelResponse } from "@vercel/node";
import { getDb, ensureSchema } from "./_lib/db.js";
import { resolveAudioUrl } from "./_lib/audio-url.js";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "GET") return res.status(405).end();
  const limit = Math.min(200, Math.max(1, parseInt(req.query.limit as string) || 50));
  const offset = Math.max(0, parseInt(req.query.offset as string) || 0);
  const db = getDb();
  await ensureSchema(db);

  const rows = await db.execute({
    sql: "SELECT date, issue_no, lead_headline, active_count, generated_at, audio_url FROM filings WHERE kind='lead' ORDER BY date DESC LIMIT ? OFFSET ?",
    args: [limit, offset],
  });
  const totalRow = await db.execute({
    sql: "SELECT COUNT(*) FROM filings WHERE kind='lead'",
    args: [],
  });

  const briefings = rows.rows.map((r) => ({
    date: r.date,
    issue_no: r.issue_no,
    lead_headline: r.lead_headline || "",
    audio_url: resolveAudioUrl(r.audio_url as string | null, r.date as string, "lead"),
    active_count: r.active_count || 0,
    filed_at: r.generated_at ? (r.generated_at as string).split("T")[1].slice(0, 5) : "",
  }));

  res.status(200).json({ briefings, total: totalRow.rows[0]?.[0] || 0 });
}
