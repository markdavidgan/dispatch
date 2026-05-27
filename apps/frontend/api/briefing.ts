import type { VercelRequest, VercelResponse } from "@vercel/node";
import { getDb, ensureSchema } from "./_lib/db.js";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "GET") return res.status(405).end();
  const date = req.query.date as string;
  if (!date) return res.status(400).json({ error: "date query param required" });
  const db = getDb();
  await ensureSchema(db);

  const rows = await db.execute({
    sql: `SELECT date, kind, issue_no, lead_headline, lead_body, active_count, project_lines, generated_at, addendum_label, addendum_body, lead_article FROM filings WHERE date = ? ORDER BY kind`,
    args: [date],
  });

  if (!rows.rows.length) return res.status(404).json({ error: `no briefing filed for ${date}` });

  const lead = rows.rows.find((r: any) => r.kind === "lead");
  if (!lead) return res.status(404).json({ error: `no lead filing for ${date}` });

  const addendums = rows.rows
    .filter((r: any) => r.kind === "addendum")
    .map((r: any) => ({
      filed_at: r.generated_at ? (r.generated_at as string).split("T")[1].slice(0, 5) : "",
      label: r.addendum_label || "",
      body: r.addendum_body || "",
    }));

  const metaRows = await db.execute({
    sql: "SELECT slug FROM projects WHERE kind = 'meta'",
    args: [],
  });
  const metaSlugs = new Set(metaRows.rows.map((r: any) => r.slug as string));
  const filteredProjects = JSON.parse((lead.project_lines as string) || "[]").filter((p: any) => !metaSlugs.has(p.slug));

  const base = process.env.R2_PUBLIC_BASE_URL?.replace(/\/$/, "") || "";

  res.status(200).json({
    date: lead.date,
    issue_no: lead.issue_no || 0,
    lead_headline: lead.lead_headline || "",
    lead_body: lead.lead_body || "",
    lead_article: lead.lead_article || "",
    addendums,
    projects: filteredProjects,
    audio_lead_url: base ? `${base}/dispatch/audio/${date}-lead.wav` : null,
    audio_addendum_url: addendums.length && base ? `${base}/dispatch/audio/${date}-addendum.wav` : null,
    active_count: lead.active_count || 0,
    filed_at: lead.generated_at ? (lead.generated_at as string).split("T")[1].slice(0, 5) : "",
    recent_events: (await db.execute({
      sql: `SELECT project_slug, kind, external_id, title, author, occurred_at, url FROM events WHERE occurred_at >= ? AND occurred_at < ? ORDER BY occurred_at DESC`,
      args: [`${date}T00:00:00Z`, `${date}T23:59:59Z`],
    })).rows.map((r: any) => ({
      project_slug: r.project_slug,
      kind: r.kind,
      external_id: r.external_id,
      title: r.title,
      author: r.author,
      occurred_at: r.occurred_at,
      url: r.url,
    })),
  });
}
