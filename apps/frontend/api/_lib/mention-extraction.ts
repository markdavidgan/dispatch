import { getDb } from "./db";

export function extractMentions(text: string, projects: Record<string, string>): Array<{ slug: string; name: string; excerpt: string; position: number }> {
  const mentions: Array<{ slug: string; name: string; excerpt: string; position: number }> = [];
  const sentences = text.split(/(?<=[.!?])\s+/);
  let position = 0;

  for (const sentence of sentences) {
    for (const [slug, name] of Object.entries(projects)) {
      const searchTerms = [slug, name];
      for (const term of searchTerms) {
        if (sentence.toLowerCase().includes(term.toLowerCase())) {
          mentions.push({ slug, name, excerpt: sentence.trim(), position });
          position++;
          break;
        }
      }
    }
  }
  return mentions;
}

export async function recordMentions(briefingDate: string, mentions: Array<{ slug: string; excerpt: string; position: number }>): Promise<void> {
  const db = getDb();
  await db.execute({
    sql: "DELETE FROM briefing_mentions WHERE briefing_date = ?",
    args: [briefingDate],
  });
  for (const m of mentions) {
    await db.execute({
      sql: "INSERT INTO briefing_mentions (briefing_date, project_slug, excerpt, position) VALUES (?, ?, ?, ?)",
      args: [briefingDate, m.slug, m.excerpt, m.position],
    });
  }
}

export async function refreshMentions(briefingDate: string): Promise<void> {
  const db = getDb();
  const projectRows = await db.execute({
    sql: "SELECT slug, display_name FROM projects WHERE status != 'archived'",
    args: [],
  });
  const projects: Record<string, string> = {};
  for (const r of projectRows.rows) {
    projects[r.slug as string] = r.display_name as string;
  }

  const filingRows = await db.execute({
    sql: "SELECT kind, lead_body, addendum_body FROM filings WHERE date = ? ORDER BY kind",
    args: [briefingDate],
  });

  const parts: string[] = [];
  for (const r of filingRows.rows) {
    if (r.kind === "lead" && r.lead_body) parts.push(r.lead_body as string);
    if (r.kind === "addendum" && r.addendum_body) parts.push(r.addendum_body as string);
  }

  const combined = parts.join("\n\n");
  const mentions = extractMentions(combined, projects);
  await recordMentions(briefingDate, mentions);
}
