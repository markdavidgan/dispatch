import crypto from "crypto";
import { getDb } from "./db.js";
import { uploadBytes } from "./storage.js";

const SNAPSHOT_KEY = "dispatch/snapshot.json";
const ARCHIVE_PREFIX = "dispatch/snapshot-archive";

function signingSecret(): string {
  return process.env.DISPATCH_SNAPSHOT_SECRET || "dispatch-dev-secret-rotate-me";
}

function signPayload(payload: Record<string, any>): string {
  const body = JSON.stringify(payload, Object.keys(payload).sort());
  return crypto.createHmac("sha256", signingSecret()).update(body).digest("hex").slice(0, 32);
}

export async function buildSnapshot(): Promise<Record<string, any>> {
  const db = getDb();
  const now = new Date().toISOString();

  // Meta slugs for filtering
  const metaRows = await db.execute({
    sql: "SELECT slug FROM projects WHERE kind = 'meta'",
    args: [],
  });
  const metaSlugs = new Set(metaRows.rows.map((r) => r.slug as string));

  // Projects
  const projectRows = await db.execute({
    sql: "SELECT slug, display_name, status, kind, color_hint, from_the_desk, from_the_desk_generated_at FROM projects WHERE kind != 'meta' ORDER BY status DESC, slug",
    args: [],
  });

  const projects: Array<Record<string, any>> = [];
  for (const row of projectRows.rows) {
    const slug = row.slug as string;
    const mentionRows = await db.execute({
      sql: "SELECT briefing_date, excerpt FROM briefing_mentions WHERE project_slug = ? ORDER BY briefing_date DESC, position ASC LIMIT 5",
      args: [slug],
    });
    projects.push({
      slug,
      name: row.display_name,
      status: row.status,
      kind: row.kind,
      color_hint: row.color_hint,
      from_the_desk: row.from_the_desk,
      from_the_desk_generated_at: row.from_the_desk_generated_at,
      mentioned_in_briefings: mentionRows.rows.map((m) => ({
        date: m.briefing_date,
        excerpt: m.excerpt,
      })),
    });
  }

  // Latest lead
  const latestRow = await db.execute({
    sql: "SELECT date FROM filings WHERE kind='lead' ORDER BY date DESC LIMIT 1",
    args: [],
  });
  const latestDate = latestRow.rows[0]?.date as string | undefined;

  let lead: Record<string, any> | null = null;
  let addendums: Array<Record<string, any>> = [];
  let leadAudioUrl: string | null = null;
  let leadAudioDur: number | null = null;
  let addendumAudioUrl: string | null = null;
  let addendumAudioDur: number | null = null;

  if (latestDate) {
    const filingRows = await db.execute({
      sql: `SELECT date, kind, issue_no, covers_from, covers_until, lead_headline, lead_body, active_count, project_lines, addendum_label, addendum_body, model, generated_at, audio_url, audio_duration_s FROM filings WHERE date = ? ORDER BY kind, id`,
      args: [latestDate],
    });

    for (const row of filingRows.rows) {
      const kind = row.kind as string;
      const generatedAt = (row.generated_at as string) || "";
      const filedAt = generatedAt.includes("T") ? generatedAt.split("T")[1].slice(0, 5) : "";

      if (kind === "lead") {
        const projectLines = JSON.parse((row.project_lines as string) || "[]");
        // Filter out meta projects that may have been included in synthesis
        const filteredProjectLines = projectLines.filter((p: any) => !metaSlugs.has(p.slug));
        lead = {
          date: row.date,
          issue_no: row.issue_no,
          filed_at: filedAt,
          active_count: `${(row.active_count as number) || 0}`.padStart(2, "0"),
          lead_headline: row.lead_headline || "",
          lead_body: row.lead_body || "",
          projects: filteredProjectLines,
          addendums: [],
          audio: null,
        };
        leadAudioUrl = (row.audio_url as string) || null;
        leadAudioDur = (row.audio_duration_s as number) || null;
      } else if (kind === "addendum") {
        addendums.push({
          filed_at: filedAt,
          label: row.addendum_label || "",
          body: row.addendum_body || "",
        });
        if (row.audio_url) {
          addendumAudioUrl = row.audio_url as string;
          addendumAudioDur = (row.audio_duration_s as number) || null;
        }
      }
    }
  }

  if (lead) {
    lead.addendums = addendums;
    const base = process.env.R2_PUBLIC_BASE_URL?.replace(/\/$/, "") || "";
    const backendUrl = process.env.BACKEND_URL?.replace(/\/$/, "") || "https://dispatch-demo-api.marklab.uk";

    let publicLead = leadAudioUrl && !leadAudioUrl.startsWith("local://") ? leadAudioUrl : (leadAudioUrl?.startsWith("local://") && base ? `${base}/${leadAudioUrl.slice(8)}` : null);
    let publicAddendum = addendumAudioUrl && !addendumAudioUrl.startsWith("local://") ? addendumAudioUrl : (addendumAudioUrl?.startsWith("local://") && base ? `${base}/${addendumAudioUrl.slice(8)}` : null);

    // Fallback to backend audio if none found locally
    if (!publicLead && latestDate) {
      publicLead = `${backendUrl}/api/audio/dispatch/audio/${latestDate}-lead.mp3`;
    }
    if (!publicAddendum && latestDate && addendums.length) {
      publicAddendum = `${backendUrl}/api/audio/dispatch/audio/${latestDate}-addendum.mp3`;
    }

    if (publicLead || publicAddendum) {
      lead.audio = {
        lead_url: publicLead,
        lead_duration_s: leadAudioDur,
        addendum_url: publicAddendum,
        addendum_duration_s: addendumAudioDur,
        voice: "Kokoro-82M",
      };
    }
  }

  // Recent events
  const eventRows = await db.execute({
    sql: "SELECT project_slug, kind, external_id, title, author, occurred_at, url FROM events ORDER BY occurred_at DESC LIMIT 50",
    args: [],
  });
  const recentEvents = eventRows.rows.map((r) => ({
    project_slug: r.project_slug,
    kind: r.kind,
    external_id: r.external_id,
    title: r.title,
    author: r.author,
    occurred_at: r.occurred_at,
    url: r.url,
  }));

  const payload: Record<string, any> = {
    version: 1,
    generated_at: now,
    brief: lead,
    projects,
    recent_events: recentEvents,
    episodes: [],
  };
  payload.signature = signPayload(payload);
  return payload;
}

export async function publishSnapshot(): Promise<{ url: string; snapshot: Record<string, any> }> {
  const snapshot = await buildSnapshot();
  const data = Buffer.from(JSON.stringify(snapshot, null, 2), "utf-8");

  const url = await uploadBytes(data, SNAPSHOT_KEY, "application/json");

  const dateStamp = new Date().toISOString().split("T")[0];
  const archiveKey = `${ARCHIVE_PREFIX}/${dateStamp}.json`;
  await uploadBytes(data, archiveKey, "application/json");

  return { url, snapshot };
}
