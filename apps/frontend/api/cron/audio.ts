import type { VercelRequest, VercelResponse } from "@vercel/node";
import { getDb } from "../_lib/db.js";
import { runAudio, runPublish } from "../_lib/orchestrator.js";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.headers["user-agent"] !== "vercel-cron/1.0") {
    return res.status(403).json({ error: "Forbidden" });
  }

  const db = getDb();

  try {
    // Find the most recent lead filing that is missing audio
    const r = await db.execute({
      sql: `SELECT date FROM filings
            WHERE kind = 'lead' AND audio_url IS NULL
            ORDER BY date DESC LIMIT 1`,
      args: [],
    });

    if (!r.rows.length) {
      return res.status(200).json({ ok: true, skipped: true, reason: "no filings missing audio" });
    }

    const date = r.rows[0].date as string;
    const audio = await runAudio("lead", date);
    const { url } = await runPublish();

    res.status(200).json({ ok: true, date, audio, snapshot_url: url });
  } catch (e) {
    console.error("audio cron failed:", e);
    res.status(500).json({ ok: false, error: String(e) });
  }
}
