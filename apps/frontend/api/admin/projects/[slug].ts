import type { VercelRequest, VercelResponse } from "@vercel/node";
import { getDb } from "../../../_lib/db";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const slug = req.query.slug as string;
  const db = getDb();

  if (req.method === "PATCH") {
    const body = req.body || {};
    const sets: string[] = [];
    const args: any[] = [];
    const fields = ["display_name", "status", "kind", "color_hint", "summary", "sort_order", "github_repo", "podcast_config"];
    for (const f of fields) {
      if (body[f] !== undefined) { sets.push(`${f} = ?`); args.push(body[f]); }
    }
    if (!sets.length) return res.status(400).json({ error: "no fields" });
    args.push(slug);
    await db.execute({ sql: `UPDATE projects SET ${sets.join(", ")} WHERE slug = ?`, args });
    res.status(200).json({ ok: true });
  } else if (req.method === "DELETE") {
    await db.execute({ sql: "DELETE FROM projects WHERE slug = ?", args: [slug] });
    res.status(200).json({ ok: true });
  } else {
    res.status(405).end();
  }
}
