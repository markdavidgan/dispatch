import { getDb } from "./db.js";
import { synthesize } from "./llm.js";
import { generateAudio, estimateDuration } from "./tts.js";
import { uploadBytes } from "./storage.js";
import { publishSnapshot } from "./snapshot.js";
import { refreshMentions } from "./mention-extraction.js";
import { deriveBullet, deriveActiveCount } from "./bullets.js";
import { lintLead } from "./brief-lint.js";
import { buildArticlePrompt, buildLeadPrompt, buildAddendumPrompt } from "./prompt.js";
import { ArticleFilingSchema, LeadFilingSchema, AddendumFilingSchema } from "./schema.js";

const TZ = process.env.DISPATCH_TZ || "Asia/Manila";

async function logRun(job: string, status: string, eventsAdded = 0, error?: string, startedAt?: string) {
  const db = getDb();
  const finishedAt = new Date().toISOString();
  await db.execute({
    sql: `INSERT INTO runs (job, status, started_at, finished_at, events_added, error) VALUES (?, ?, ?, ?, ?, ?)`,
    args: [job, status, startedAt || finishedAt, finishedAt, eventsAdded, error || null],
  });
}

async function eventsForWindow(coversFrom: string, coversUntil: string): Promise<Record<string, Array<Record<string, any>>>> {
  const db = getDb();
  const rows = await db.execute({
    sql: `SELECT project_slug, kind, external_id, title, author, occurred_at, url FROM events WHERE occurred_at >= ? AND occurred_at <= ? ORDER BY occurred_at DESC`,
    args: [coversFrom, coversUntil],
  });

  const byProject: Record<string, Array<Record<string, any>>> = {};
  for (const r of rows.rows) {
    const slug = r.project_slug as string;
    byProject[slug] = byProject[slug] || [];
    byProject[slug].push({
      project_slug: slug,
      kind: r.kind,
      external_id: r.external_id,
      title: r.title,
      author: r.author,
      occurred_at: r.occurred_at,
      url: r.url,
    });
  }
  return byProject;
}

async function projectInput(eventsByProject: Record<string, Array<Record<string, any>>>): Promise<Array<Record<string, any>>> {
  const db = getDb();
  const projectRows = await db.execute({
    sql: "SELECT slug, display_name, status, github_repo FROM projects WHERE status != 'archived' ORDER BY sort_order, slug",
    args: [],
  });

  const lines: Array<Record<string, any>> = [];
  for (const p of projectRows.rows) {
    const slug = p.slug as string;
    const evs = eventsByProject[slug] || [];
    const bullet = deriveBullet(p.status as string, evs);
    const commits = evs.filter((e) => e.kind === "commit").length;
    const prsOpened = evs.filter((e) => e.kind === "pr_opened").length;
    const prsMerged = evs.filter((e) => e.kind === "pr_merged").length;
    const releases = evs.filter((e) => e.kind === "release").length;

    const statParts: string[] = [];
    if (commits) statParts.push(`${commits} commit${commits !== 1 ? "s" : ""}`);
    if (prsOpened || prsMerged) statParts.push(`${prsOpened + prsMerged} PR${prsOpened + prsMerged !== 1 ? "s" : ""}`);
    if (releases) statParts.push(`${releases} release${releases !== 1 ? "s" : ""}`);
    const stat = statParts.join(" · ") || "Quiet";

    lines.push({ slug, name: p.display_name, status: p.status, stat, bullet });
  }
  return lines;
}

async function nextIssueNo(): Promise<number> {
  const db = getDb();
  const row = await db.execute({
    sql: "SELECT COALESCE(MAX(issue_no), 0) + 1 FROM filings WHERE kind='lead'",
    args: [],
  });
  return (row.rows[0]?.[0] as number) || 1;
}

async function isLeadCovered(dateStr: string): Promise<boolean> {
  const db = getDb();
  const row = await db.execute({
    sql: "SELECT 1 FROM filings WHERE date=? AND kind='lead' LIMIT 1",
    args: [dateStr],
  });
  return row.rows.length > 0;
}

async function hasEventsOn(dateStr: string): Promise<boolean> {
  const events = await eventsForWindow(
    `${dateStr}T00:00:00+00:00`,
    `${dateStr}T23:59:59+00:00`
  );
  return Object.values(events).some((arr) => arr.length > 0);
}

async function findLatestUncoveredDayWithActivity(lookBackDays = 30): Promise<string | null> {
  const today = new Date();
  const earliest = new Date(today);
  earliest.setDate(earliest.getDate() - lookBackDays);
  const latest = new Date(today);
  latest.setDate(latest.getDate() - 1);

  const db = getDb();
  const rows = await db.execute({
    sql: `SELECT DISTINCT DATE(occurred_at) AS d FROM events
          WHERE DATE(occurred_at) BETWEEN ? AND ?
            AND DATE(occurred_at) NOT IN (SELECT date FROM filings WHERE kind='lead')
          ORDER BY d DESC LIMIT 1`,
    args: [earliest.toISOString().split("T")[0], latest.toISOString().split("T")[0]],
  });
  return rows.rows[0]?.d as string | undefined || null;
}

async function resolveTargetDate(): Promise<{ date: string | null; reason: string }> {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  const dateStr = yesterday.toISOString().split("T")[0];

  if (await isLeadCovered(dateStr)) return { date: null, reason: "yesterday already covered" };
  if (!(await hasEventsOn(dateStr))) return { date: null, reason: "no events yesterday (quiet day, skipping)" };
  return { date: dateStr, reason: "yesterday" };
}

export async function runSynthesisLead(targetDate?: string): Promise<Record<string, any>> {
  const db = getDb();
  let dateLocal: string;
  let chosenReason: string;

  if (targetDate) {
    dateLocal = targetDate;
    chosenReason = "explicit";
  } else {
    const resolved = await resolveTargetDate();
    if (!resolved.date) {
      await logRun("synthesis:lead", "skipped");
      return { date: null, skipped: true, reason: resolved.reason };
    }
    dateLocal = resolved.date;
    chosenReason = resolved.reason;
  }

  const coversFrom = `${dateLocal}T00:00:00+00:00`;
  const coversUntil = `${dateLocal}T23:59:59+00:00`;
  const events = await eventsForWindow(coversFrom, coversUntil);

  if (!Object.values(events).some((arr) => arr.length > 0)) {
    await logRun("synthesis:lead", "skipped");
    return { date: dateLocal, skipped: true, reason: "no events" };
  }

  // Reuse existing issue_no if re-synthesizing same date
  const existingRow = await db.execute({
    sql: "SELECT issue_no FROM filings WHERE date=? AND kind='lead'",
    args: [dateLocal],
  });
  const issueNo = (existingRow.rows[0]?.issue_no as number) || (await nextIssueNo());
  const projects = await projectInput(events);
  const activeCount = deriveActiveCount(projects);

  // Pass A: Article
  const { prompt: articlePrompt, hash: articleHash } = buildArticlePrompt({
    issueNo,
    dateLocal,
    tz: TZ,
    coversFrom,
    coversUntil,
    projectsInput: projects,
    eventsByProject: events,
  });
  const articleResult = await synthesize(articlePrompt, ArticleFilingSchema);
  const articleText = articleResult.article.trim();

  // Pass B: Lead
  const { prompt: leadPrompt, hash: promptHash } = buildLeadPrompt({
    issueNo,
    dateLocal,
    tz: TZ,
    coversFrom,
    coversUntil,
    projectsInput: projects,
    eventsByProject: events,
    article: articleText,
  });
  const result = await synthesize(leadPrompt, LeadFilingSchema);

  // Enforce deterministic active_count
  if (result.active_count !== parseInt(activeCount)) {
    result.active_count = parseInt(activeCount);
  }

  // Lint (non-blocking)
  const warnings = lintLead(result);
  if (warnings.length) console.warn("brief lint warnings:", warnings);

  // Persist
  const generatedAt = new Date().toISOString();
  const modelName = (() => {
    const provider = process.env.DISPATCH_AI_PROVIDER || "kimi";
    if (provider === "kimi") return "kimi-for-coding";
    if (provider === "groq") return "groq-llama-3.3-70b";
    return "gemini-2.5-flash";
  })();

  await db.execute({
    sql: `INSERT INTO filings
      (date, kind, issue_no, covers_from, covers_until, lead_headline, lead_body, lead_article, active_count, project_lines, model, prompt_hash, generated_at, raw_response)
      VALUES (?, 'lead', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(date, kind) DO UPDATE SET
        issue_no=excluded.issue_no, covers_from=excluded.covers_from, covers_until=excluded.covers_until,
        lead_headline=excluded.lead_headline, lead_body=excluded.lead_body, lead_article=excluded.lead_article,
        active_count=excluded.active_count, project_lines=excluded.project_lines,
        model=excluded.model, prompt_hash=excluded.prompt_hash, generated_at=excluded.generated_at, raw_response=excluded.raw_response`,
    args: [
      dateLocal, issueNo, coversFrom, coversUntil,
      result.lead_headline, result.lead_body, articleText,
      result.active_count,
      JSON.stringify(result.project_lines),
      modelName, promptHash, generatedAt,
      JSON.stringify(result),
    ],
  });

  await refreshMentions(dateLocal);
  await logRun("synthesis:lead", "ok");

  return {
    date: dateLocal,
    issue_no: issueNo,
    headline: result.lead_headline,
    body: result.lead_body,
    model: modelName,
  };
}

export async function runSynthesisAddendum(): Promise<Record<string, any>> {
  const db = getDb();
  const now = new Date();
  const today = now.toISOString().split("T")[0];
  const coversFrom = `${today}T00:00:00+00:00`;
  const coversUntil = now.toISOString();

  const leadRow = await db.execute({
    sql: "SELECT lead_headline, lead_body, active_count, project_lines FROM filings WHERE date=? AND kind='lead'",
    args: [today],
  });
  if (!leadRow.rows.length) {
    throw new Error("No lead found for today — cannot addendum without lead");
  }

  const lead = leadRow.rows[0];
  const events = await eventsForWindow(coversFrom, coversUntil);
  const projects = await projectInput(events);

  const { prompt, hash } = buildAddendumPrompt({
    dateLocal: today,
    tz: TZ,
    leadHeadline: lead.lead_headline as string || "",
    leadBody: lead.lead_body as string || "",
    projectsInput: projects,
    eventsByProject: events,
  });

  const result = await synthesize(prompt, AddendumFilingSchema);
  const generatedAt = new Date().toISOString();
  const modelName = (() => {
    const provider = process.env.DISPATCH_AI_PROVIDER || "kimi";
    if (provider === "kimi") return "kimi-for-coding";
    if (provider === "groq") return "groq-llama-3.3-70b";
    return "gemini-2.5-flash";
  })();

  const label = `Filed since ${generatedAt.split("T")[1].slice(0, 5)}`;

  await db.execute({
    sql: `INSERT INTO filings
      (date, kind, issue_no, covers_from, covers_until, addendum_label, addendum_body, active_count, project_lines, model, prompt_hash, generated_at, raw_response)
      VALUES (?, 'addendum', NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(date, kind) DO UPDATE SET
        covers_from=excluded.covers_from, covers_until=excluded.covers_until,
        addendum_label=excluded.addendum_label, addendum_body=excluded.addendum_body,
        active_count=excluded.active_count, project_lines=excluded.project_lines,
        model=excluded.model, prompt_hash=excluded.prompt_hash, generated_at=excluded.generated_at, raw_response=excluded.raw_response`,
    args: [
      today, coversFrom, coversUntil, label, result.body,
      lead.active_count as number || 0,
      lead.project_lines as string || "[]",
      modelName, hash, generatedAt,
      JSON.stringify(result),
    ],
  });

  await refreshMentions(today);
  await logRun("synthesis:addendum", "ok");

  return { date: today, label, body: result.body, model: modelName };
}

export async function runAudio(kind: "lead" | "addendum" = "lead", targetDate?: string, text?: string): Promise<Record<string, any>> {
  const db = getDb();

  let row: Record<string, any>;
  if (targetDate) {
    const r = await db.execute({
      sql: "SELECT date, lead_headline, lead_body, lead_article, addendum_label, addendum_body FROM filings WHERE kind=? AND date=? ORDER BY id DESC LIMIT 1",
      args: [kind, targetDate],
    });
    row = r.rows[0] || null;
  } else {
    const r = await db.execute({
      sql: "SELECT date, lead_headline, lead_body, lead_article, addendum_label, addendum_body FROM filings WHERE kind=? ORDER BY date DESC, id DESC LIMIT 1",
      args: [kind],
    });
    row = r.rows[0] || null;
  }

  if (!row) throw new Error(`No ${kind} filing to generate audio for`);

  const filingDate = row.date as string;
  if (!text) {
    if (kind === "lead") {
      const body = row.lead_article || row.lead_body || "";
      text = `${row.lead_headline}. ${body}`;
    } else {
      text = `${row.addendum_label || ""}. ${row.addendum_body || ""}`;
    }
  }

  const mp3 = await generateAudio(text);
  const duration = estimateDuration(text);
  const r2Key = `dispatch/audio/${filingDate}-${kind}.mp3`;
  const url = await uploadBytes(mp3, r2Key, "audio/mpeg");

  await db.execute({
    sql: "UPDATE filings SET audio_url=?, audio_duration_s=? WHERE date=? AND kind=?",
    args: [url, duration, filingDate, kind],
  });

  await logRun(`audio:generate:${kind}`, "ok");
  return { url, duration, kind };
}

export async function runPublish(): Promise<{ url: string; snapshot: Record<string, any> }> {
  const started = new Date().toISOString();
  const result = await publishSnapshot();
  await logRun("publish:snapshot", "ok", 0, undefined, started);
  return result;
}

export async function runIngestGitHub(): Promise<number> {
  const db = getDb();
  const projectRows = await db.execute({
    sql: "SELECT slug, github_repo FROM projects WHERE github_repo IS NOT NULL",
    args: [],
  });

  let total = 0;
  for (const p of projectRows.rows) {
    const { ingestRepo } = await import("./ingest-github");
    try {
      const n = await ingestRepo(p.slug as string, p.github_repo as string);
      total += n;
    } catch (e) {
      console.error("github ingest failed for", p.slug, e);
    }
  }

  await logRun("ingest:github", total > 0 ? "ok" : "skipped", total);
  return total;
}

export async function runIngestGitHubCommits(): Promise<number> {
  const db = getDb();
  const projectRows = await db.execute({
    sql: "SELECT slug, github_repo FROM projects WHERE github_repo IS NOT NULL",
    args: [],
  });

  let total = 0;
  for (const p of projectRows.rows) {
    const { ingestCommits } = await import("./ingest-github-commits");
    try {
      const n = await ingestCommits(p.slug as string, p.github_repo as string);
      total += n;
    } catch (e) {
      console.error("github commits ingest failed for", p.slug, e);
    }
  }

  await logRun("ingest:github_commits", total > 0 ? "ok" : "skipped", total);
  return total;
}

export async function runHousekeeping(): Promise<void> {
  const db = getDb();
  // Delete old runs (keep 30 days)
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - 30);
  await db.execute({
    sql: "DELETE FROM runs WHERE started_at < ?",
    args: [cutoff.toISOString()],
  });
  await logRun("housekeeping", "ok");
}

export { findLatestUncoveredDayWithActivity };
