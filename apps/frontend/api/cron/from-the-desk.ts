import type { VercelRequest, VercelResponse } from "@vercel/node";
import { getDb } from "../../_lib/db";
import { synthesize } from "../../_lib/llm";
import { z } from "zod";

const SummarySchema = z.object({ body: z.string() });

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.headers["user-agent"] !== "vercel-cron/1.0") {
    return res.status(403).json({ error: "Forbidden" });
  }

  const db = getDb();
  const since = new Date();
  since.setDate(since.getDate() - 7);

  const projects = await db.execute({
    sql: "SELECT slug, display_name FROM projects WHERE status != 'archived'",
    args: [],
  });

  for (const p of projects.rows) {
    const slug = p.slug as string;
    const displayName = p.display_name as string;
    const events = await db.execute({
      sql: "SELECT kind, title FROM events WHERE project_slug = ? AND occurred_at >= ? ORDER BY occurred_at DESC",
      args: [slug, since.toISOString()],
    });

    if (events.rows.length < 2) {
      await db.execute({
        sql: "UPDATE projects SET from_the_desk = ?, from_the_desk_generated_at = ? WHERE slug = ?",
        args: ["Quiet this week.", new Date().toISOString(), slug],
      });
      continue;
    }

    const lines = [`Weekly summary for ${displayName}`, ""];
    for (const e of events.rows) {
      lines.push(`- [${e.kind}] ${e.title}`);
    }
    lines.push("");
    lines.push("Write a concise 2-3 sentence summary of this week's activity.");

    try {
      const result = await synthesize(lines.join("\n"), SummarySchema);
      await db.execute({
        sql: "UPDATE projects SET from_the_desk = ?, from_the_desk_generated_at = ? WHERE slug = ?",
        args: [result.body.trim(), new Date().toISOString(), slug],
      });
    } catch (e) {
      console.error("from_the_desk failed for", slug, e);
    }
  }

  res.status(200).json({ ok: true });
}
