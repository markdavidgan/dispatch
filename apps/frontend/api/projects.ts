import type { VercelRequest, VercelResponse } from "@vercel/node";
import { getDb } from "./_lib/db";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "GET") return res.status(405).end();
  const db = getDb();

  const rows = await db.execute({
    sql: "SELECT slug, display_name, status, kind, color_hint, summary, sort_order FROM projects WHERE kind != 'meta' ORDER BY sort_order, slug",
    args: [],
  });

  const projects = rows.rows.map((r) => ({
    slug: r.slug,
    name: r.display_name,
    status: r.status,
    kind: r.kind,
    color_hint: r.color_hint,
    summary: r.summary,
    sort_order: r.sort_order,
  }));

  res.status(200).json({ projects });
}
