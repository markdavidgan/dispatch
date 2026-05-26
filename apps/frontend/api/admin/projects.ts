import type { VercelRequest, VercelResponse } from "@vercel/node";
import { getDb } from "../../lib/db";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const db = getDb();
  if (req.method === "GET") {
    const rows = await db.execute({
      sql: "SELECT slug, display_name, status, kind, color_hint, summary, sort_order, github_repo, podcast_config, from_the_desk, from_the_desk_generated_at FROM projects ORDER BY sort_order, slug",
      args: [],
    });
    res.status(200).json({ projects: rows.rows });
  } else if (req.method === "POST") {
    const body = req.body || {};
    await db.execute({
      sql: `INSERT INTO projects (slug, display_name, status, kind, color_hint, summary, sort_order, github_repo, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
              display_name=excluded.display_name, status=excluded.status, kind=excluded.kind,
              color_hint=excluded.color_hint, summary=excluded.summary, sort_order=excluded.sort_order,
              github_repo=excluded.github_repo`,
      args: [
        body.slug, body.display_name, body.status || "active", body.kind || "project",
        body.color_hint, body.summary, body.sort_order || 0, body.github_repo,
        new Date().toISOString(),
      ],
    });
    res.status(200).json({ ok: true });
  } else {
    res.status(405).end();
  }
}
