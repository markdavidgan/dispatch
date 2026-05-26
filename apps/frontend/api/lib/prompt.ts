import crypto from "crypto";

const LEAD_SYSTEM = `You are writing for Dispatch, a private daily editorial brief for a software engineer who runs a homelab and ships a handful of personal projects. Apply the creative-writing skill at Technical/Journalistic register (Ars Technica dial), dialed back toward Monocle restraint: precise, calm, slightly dry. No hype, no "excited to announce", no clichés. The reader is the engineer himself.`;

const ARTICLE_SYSTEM = `You are writing the daily briefing for Dispatch — a private editorial for a software engineer who runs a homelab and ships a handful of personal projects. Apply the creative-writing skill at Technical/Journalistic register, Ars Technica dial dialed back toward Monocle restraint. The reader is the engineer himself; he already knows the projects exist, so don't re-introduce them. He listens to this every morning, so it must be short.

## Length

Pick ONE of three modes based on the day's data — match length to substance, never inflate.

**Digest (default — ~200 words, ~80 seconds aloud).** Two paragraphs. Use this for ordinary days: feature work, bug fixes, refactors, incremental progress. Lead with the most consequential movement; walk the rest in priority order; stop. No closing flourish unless one is genuinely visible in the data.

**Digest + explainer (~300 words max, ~2 minutes aloud).** Use this ONLY when a genuinely new concept, technique, or idea shipped today — something the reader would benefit from a one-paragraph plain-language explanation of. Do NOT trigger this mode for routine work, bug fixes, or restatements of yesterday's concepts.

**Long-form (~700 words max, ~5 minutes aloud).** Use this when the day is genuinely busy across several projects AND there's enough distinct thematic material to support extended prose without padding. Structure: open with the headline movement; devote a focused paragraph to each of the day's distinct narrative threads (typically 3–5); close with the quietest signal that still matters.

## Style

Cite specific events — "the WebSocket reconnection bug landed in the trader app", not generic "made progress". Narrative prose, not bullet points.

Hard rules: no exclamation marks, no second person, no "excited to announce", no "leverage", no "in today's fast-paced", no bulleted lists, no headings inside the prose.`;

const ADDENDUM_SYSTEM = `You are writing for Dispatch, a private daily editorial brief. This is a rolling addendum — a short update filed after the morning lead. Apply the creative-writing skill at Technical/Journalistic register, Monocle restraint. Report only *new* movement since the lead below. One or two sentences. Calm, precise, no hype.`;

export function buildArticlePrompt(params: {
  issueNo: number;
  dateLocal: string;
  tz: string;
  coversFrom: string;
  coversUntil: string;
  projectsInput: Array<Record<string, any>>;
  eventsByProject: Record<string, Array<Record<string, any>>>;
}): { prompt: string; hash: string } {
  const lines: string[] = [];
  lines.push(ARTICLE_SYSTEM);
  lines.push("");
  lines.push("## Window");
  lines.push(`- Issue No. ${params.issueNo} — ${params.dateLocal}`);
  lines.push(`- Covers: ${params.coversFrom} → ${params.coversUntil} (${params.tz})`);
  lines.push("");
  const nameBySlug: Record<string, string> = {};
  for (const p of params.projectsInput) nameBySlug[p.slug] = p.name;
  lines.push("## Projects (input — for orientation)");
  for (const p of params.projectsInput) {
    lines.push(`- ${p.slug} (${p.name}) [${p.status}] bullet=${p.bullet} stat=${p.stat}`);
  }
  lines.push("");
  lines.push("## Data");
  for (const [slug, events] of Object.entries(params.eventsByProject)) {
    if (!events.length) continue;
    const displayName = nameBySlug[slug] || slug;
    lines.push(`### ${slug} (${displayName})`);
    for (const e of events) {
      const t = (e.occurred_at as string).split("T")[1]?.slice(0, 5) || "";
      lines.push(`- ${t} ${e.kind.padStart(11)} ${e.title}`);
    }
    lines.push("");
  }
  lines.push("## Output");
  lines.push("Return ONLY a JSON object — no prose around it, no code fences:");
  lines.push(JSON.stringify({ article: "the briefing prose. ~200 words / 2 short paragraphs by default; up to ~300 words when a genuinely new concept shipped today; up to ~700 words / 3–5 focused paragraphs on busy multi-project days with distinct narrative threads (see system message). Paragraphs separated by blank lines." }, null, 2));

  const text = lines.join("\n");
  const hash = crypto.createHash("sha256").update(text).digest("hex").slice(0, 16);
  return { prompt: text, hash };
}

export function buildLeadPrompt(params: {
  issueNo: number;
  dateLocal: string;
  tz: string;
  coversFrom: string;
  coversUntil: string;
  projectsInput: Array<Record<string, any>>;
  eventsByProject: Record<string, Array<Record<string, any>>>;
  article?: string;
}): { prompt: string; hash: string } {
  const lines: string[] = [];
  lines.push(LEAD_SYSTEM);
  lines.push("");
  lines.push("## Window");
  lines.push(`- Issue No. ${params.issueNo} — ${params.dateLocal}`);
  lines.push(`- Covers: ${params.coversFrom} → ${params.coversUntil} (${params.tz})`);
  lines.push("");
  const nameBySlug: Record<string, string> = {};
  for (const p of params.projectsInput) nameBySlug[p.slug] = p.name;
  lines.push("## Projects (input — bullet already computed)");
  for (const p of params.projectsInput) {
    lines.push(`- ${p.slug} (${p.name}) [${p.status}] bullet=${p.bullet} stat=${p.stat}`);
  }
  lines.push("");
  if (params.article) {
    lines.push("## Article (already written — summarize, don't invent)");
    lines.push("The dek (lead_body) must compress this article's opening claim into 2-3 sentences. The headline must reflect the article's central point. Do not introduce facts that are not in the article.");
    lines.push("");
    lines.push(params.article);
    lines.push("");
  }
  lines.push("## Data");
  for (const [slug, events] of Object.entries(params.eventsByProject)) {
    if (!events.length) continue;
    const displayName = nameBySlug[slug] || slug;
    lines.push(`### ${slug} (${displayName})`);
    for (const e of events) {
      const t = (e.occurred_at as string).split("T")[1]?.slice(0, 5) || "";
      lines.push(`- ${t} ${e.kind.padStart(11)} ${e.title}`);
    }
    lines.push("");
  }
  lines.push("## Output");
  lines.push("Return ONLY a JSON object matching this schema, no prose, no code fences:");
  lines.push(JSON.stringify({
    lead_headline: "string, <=120 chars, sentence case",
    lead_body: "string, 2-3 sentences, <=280 chars, narrative not bulleted",
    active_count: "two-digit string like '03'",
    project_lines: [
      { slug: "<slug>", name: "<display name>", status: "active|held", stat: "<short caps phrase>", bullet: "red|amber|sand" }
    ],
  }, null, 2));

  const text = lines.join("\n");
  const hash = crypto.createHash("sha256").update(text).digest("hex").slice(0, 16);
  return { prompt: text, hash };
}

export function buildAddendumPrompt(params: {
  dateLocal: string;
  tz: string;
  leadHeadline: string;
  leadBody: string;
  projectsInput: Array<Record<string, any>>;
  eventsByProject: Record<string, Array<Record<string, any>>>;
}): { prompt: string; hash: string } {
  const lines: string[] = [];
  lines.push(ADDENDUM_SYSTEM);
  lines.push("");
  lines.push("## Window");
  lines.push(`- Date: ${params.dateLocal} (${params.tz})`);
  lines.push("- This addendum covers movement since the morning lead.");
  lines.push("");
  lines.push("## Morning lead (for context — do not repeat)");
  lines.push(`Headline: ${params.leadHeadline}`);
  lines.push(`Body: ${params.leadBody}`);
  lines.push("");
  const nameBySlug: Record<string, string> = {};
  for (const p of params.projectsInput) nameBySlug[p.slug] = p.name;
  lines.push("## Projects (current state)");
  for (const p of params.projectsInput) {
    lines.push(`- ${p.slug} (${p.name}) [${p.status}] bullet=${p.bullet} stat=${p.stat}`);
  }
  lines.push("");
  lines.push("## New data since lead");
  for (const [slug, events] of Object.entries(params.eventsByProject)) {
    if (!events.length) continue;
    const displayName = nameBySlug[slug] || slug;
    lines.push(`### ${slug} (${displayName})`);
    for (const e of events) {
      const t = (e.occurred_at as string).split("T")[1]?.slice(0, 5) || "";
      lines.push(`- ${t} ${e.kind.padStart(11)} ${e.title}`);
    }
    lines.push("");
  }
  lines.push("## Output");
  lines.push("Return ONLY a JSON object, no prose, no code fences:");
  lines.push(JSON.stringify({ addendum_body: "string, 1-2 sentences, <=200 chars, only new movement" }, null, 2));

  const text = lines.join("\n");
  const hash = crypto.createHash("sha256").update(text).digest("hex").slice(0, 16);
  return { prompt: text, hash };
}
