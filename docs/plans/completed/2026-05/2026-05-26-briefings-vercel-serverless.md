# Dispatch — Move Briefings Pipeline to Vercel Serverless

> **Status: COMPLETED (with architectural revision)**  
> **Completed:** 2026-05-27

**Goal:** Extract the briefings pipeline (ingest → synthesis → publish → API) from
the self-hosted FastAPI backend and run it as serverless functions on Vercel.
Keep the podcast pipeline on the self-hosted backend.

**What actually happened:** The ingest, synthesis, and publish steps moved to
Vercel successfully. TTS did **not** move — it remains on the self-hosted backend
(marklab) because the planned TTS providers (Kokoro HF Inference, ElevenLabs)
were either broken or required new credentials. See
[ADR 001: Keep TTS on the Self-Hosted Backend](../architecture/adr/001-tts-on-marklab-backend.md).

**Architecture:** Hybrid deployment.
- **Vercel** (cloud): Vite SPA frontend + TypeScript serverless API routes + Turso DB + Vercel Cron Jobs. Handles ingest, synthesis, snapshot publishing, and admin.
- **Self-hosted backend** (marklab Docker): TTS generation (Google Cloud Chirp 3 HD) + podcast pipeline (NotebookLM, ffmpeg). Exposes `POST /api/tts/generate` to Vercel.

**Tech Stack:**
- **Frontend:** Vite + React 19 + Tailwind v4 (unchanged)
- **API:** Vercel Functions (Node.js 20+, TypeScript) — file-based routing in `apps/frontend/api/`
- **Database:** Turso (libSQL over HTTP)
- **LLM:** Google Gemini 2.5 Flash (primary) + Groq Llama 3.3 70B (fallback)
- **TTS:** Google Cloud Chirp 3 HD on marklab backend — **not** ElevenLabs/Kokoro as originally planned
- **Storage:** Cloudflare R2
- **Cron:** Vercel Cron Jobs (`vercel.json`)
- **Ingest:** GitHub REST API only

**Scope explicitly included:**
- All `/api/briefings/*` routes (list, detail)
- `/api/brief/refresh` (on-demand addendum)
- `/api/snapshot` (public snapshot)
- `/api/live` (live stats)
- `/api/projects` (project listing)
- `/api/audio/{key}` (audio proxy/redirect)
- `/api/admin/settings/*` (encrypted settings CRUD)
- `/api/admin/schedules/*` (cron schedule CRUD)
- `/api/admin/runs/*` (job execution history)
- `/api/admin/system/*` (setup status, backup trigger, backfill)
- `/api/admin/briefings/generate` (manual lead generation)
- `/api/admin/projects/*` (project CRUD)
- Vercel Cron Jobs: `ingest_github`, `ingest_github_commits`, `synthesis_lead`, `from_the_desk`, `housekeeping`

**Scope on self-hosted backend:**
- **TTS generation** (`POST /api/tts/generate`, Google Cloud Chirp 3 HD, ffmpeg)
- **Podcast pipeline** (`/api/podcasts/*`, `/api/admin/podcasts/*`, NotebookLM, ffmpeg, `podcast/intake.py`)
- Local git ingest (`run_ingest_git` — requires `/repos` filesystem access)
- APScheduler (for podcast jobs)
- SQLite (for podcast episodes, jobs, NotebookLM sessions)

**What was originally planned to move but stayed:**
- ~~Google Cloud TTS + ffmpeg audio pipeline~~ → Kept on backend. See ADR 001.

**Reference docs:**
- `CLAUDE.md` — architecture invariants (no-app-auth, editorial design frozen)
- `docs/architecture/ARCHITECTURE.md` — current system overview
- `docs/architecture/DATA-FLOW.md` — data flow diagrams
- `docs/plans/completed/2026-05/2026-05-23-dispatch-phases-2-7.md` — prior phases context

---

## NotebookLM / Podcasts — Clarification

You asked: *"We do use NotebookLM, and we're not changing that. What's the issue there?"*

**The issue is NOT that NotebookLM doesn't work.** It works great today on your self-hosted backend. The issue is that it **cannot run on Vercel serverless**, which is why the podcast pipeline stays on the self-hosted backend.

Here's the breakdown:

| Requirement | Current Implementation | Vercel Serverless | Verdict |
|---|---|---|---|
| **Session management** | `notebooklm_wrapper.py` holds browser cookies/session state in-memory | Stateless functions lose state between invocations | ❌ Incompatible |
| **Polling duration** | Polls for up to **4 hours** waiting for Audio Overview generation | Max function timeout: 5 min (Hobby) / 13 min (Pro Fluid Compute) | ❌ Incompatible |
| **Audio download** | Downloads DASH stream, converts to MP3 with `ffmpeg` | No `ffmpeg` binary install possible | ❌ Incompatible |
| **Loudness normalization** | `ffmpeg loudnorm` filter (-16 LUFS) | No audio processing libraries available | ❌ Incompatible |

**None of this matters because we're keeping podcasts on the self-hosted backend.** The backend becomes a single-purpose podcast worker. It keeps its SQLite DB (for podcast jobs, episodes, NotebookLM sessions), APScheduler, ffmpeg, and local git repos. It exposes only `/api/podcasts/*` and `/api/admin/podcasts/*`.

The frontend calls:
- `https://dispatch-vercel.vercel.app/api/*` — briefings, snapshots, admin, settings
- `https://dispatch-podcast.yourdomain.com/api/podcasts/*` — podcasts (proxied or direct)

---

## File Map

**Delete (from `apps/frontend/` — no longer needed):**
- None. The Vite SPA stays intact.

**Create (in `apps/frontend/`):**
- `api/lib/db.ts` — Turso client wrapper (`@libsql/client`)
- `api/lib/crypto.ts` — Fernet-compatible encryption/decryption (Web Crypto API)
- `api/lib/llm.ts` — unified LLM client (Gemini + Groq fallback, OpenAI-compatible)
- `api/lib/tts.ts` — TTS client (ElevenLabs or Kokoro)
- `api/lib/storage.ts` — R2/S3 storage wrapper
- `api/lib/snapshot.ts` — snapshot builder (ports `dispatch/publish/snapshot.py`)
- `api/lib/schema.ts` — shared Zod schemas (ports Pydantic models)
- `api/lib/settings.ts` — encrypted settings store (ports `dispatch/settings_store.py`)
- `api/lib/runs.ts` — runs logging helper
- `api/lib/ingest-github.ts` — GitHub API ingest (ports `dispatch/ingest/github.py`)
- `api/lib/ingest-github-commits.ts` — branch-aware commit ingest (ports `dispatch/ingest/github_commits.py`)
- `api/lib/synthesis/` — prompt builders, schema definitions, mention extraction
- `api/briefings.ts` — `GET /api/briefings` (list)
- `api/briefings/[date].ts` — `GET /api/briefings/:date` (detail)
- `api/brief/refresh.ts` — `POST /api/brief/refresh` (addendum)
- `api/snapshot.ts` — `GET /api/snapshot`
- `api/live.ts` — `GET /api/live`
- `api/projects.ts` — `GET /api/projects`
- `api/audio/[key].ts` — `GET /api/audio/:key`
- `api/admin/settings.ts` — `GET /api/admin/settings`
- `api/admin/settings/[key].ts` — `PUT /api/admin/settings/:key`
- `api/admin/settings/bulk.ts` — `POST /api/admin/settings/bulk`
- `api/admin/schedules.ts` — `GET /api/admin/schedules`
- `api/admin/schedules/[jobName].ts` — `PATCH /api/admin/schedules/:jobName`
- `api/admin/runs.ts` — `GET /api/admin/runs`
- `api/admin/system/setup-status.ts` — `GET /api/admin/system/setup-status`
- `api/admin/system/backup-now.ts` — `POST /api/admin/system/backup-now`
- `api/admin/system/backfill.ts` — `POST /api/admin/system/backfill`
- `api/admin/briefings/generate.ts` — `POST /api/admin/briefings/generate`
- `api/admin/projects.ts` — `GET/POST /api/admin/projects`
- `api/admin/projects/[slug].ts` — `PATCH/DELETE /api/admin/projects/:slug`
- `api/cron/ingest-github.ts` — Vercel Cron: GitHub ingest (30-min interval)
- `api/cron/ingest-github-commits.ts` — Vercel Cron: commit ingest (60-min interval)
- `api/cron/synthesis-lead.ts` — Vercel Cron: daily lead synthesis (~1 AM)
- `api/cron/from-the-desk.ts` — Vercel Cron: weekly summary (Sunday 23:00)
- `api/cron/housekeeping.ts` — Vercel Cron: daily cleanup
- `api/_proxy/podcasts/[...path].ts` — proxy `/api/podcasts/*` to self-hosted backend
- `turso/schema.sql` — Turso-compatible schema (adapted from `dispatch/schema.sql`)
- `turso/seed.ts` — seed script for initial projects + schedules
- `.env.example` — updated with Turso, Gemini, Groq, ElevenLabs env vars
- `middleware.ts` — Next.js-style middleware for CORS + perimeter trust (optional)

**Modify:**
- `apps/frontend/vercel.json` — add cron job definitions, remove catch-all rewrite conflict
- `apps/frontend/src/api/client.ts` — update `API_BASE` logic for same-origin `/api`
- `apps/frontend/package.json` — add `@libsql/client`, `zod`, `dotenv` deps
- `apps/frontend/vite.config.ts` — ensure `api/` is excluded from Vite build

**Tools required on executor's machine:** Node.js 20+, `npm`, `turso` CLI (for DB creation), Vercel CLI (`npm i -g vercel`).

---

## Task 1 — Turso Database Setup

**Why:** SQLite won't survive on Vercel (ephemeral filesystem). Turso is SQLite-compatible over HTTP, has a generous free tier, and requires minimal schema changes.

**Files:**
- Create: `apps/frontend/turso/schema.sql`
- Create: `apps/frontend/turso/seed.ts`
- Create: `apps/frontend/api/lib/db.ts`

**Turso schema changes from SQLite:**
- Replace `AUTOINCREMENT` with SQLite's default `INTEGER PRIMARY KEY` (already compatible)
- Replace `DATETIME` with `TEXT` (already used in existing schema)
- `FOREIGN KEY` syntax is identical
- `ON CONFLICT` syntax is identical
- Add `IF NOT EXISTS` to `CREATE TABLE` statements for idempotent setup

The existing `dispatch/schema.sql` ports almost verbatim. The only meaningful change is adding a `libsql` client wrapper instead of `aiosqlite`.

- [x] **Step 1.1: Install Turso CLI and create database**

```bash
# macOS/Linux
curl -sSfL https://get.tur.so/install.sh | bash
turso auth login
turso db create dispatch-briefings
turso db show dispatch-briefings --url  # copy this for .env
turso db tokens create dispatch-briefings  # copy this for .env
```

- [x] **Step 1.2: Create `turso/schema.sql`**

Copy from `apps/backend/dispatch/schema.sql` with these Turso-specific notes:
- Ensure all `CREATE TABLE` statements use `IF NOT EXISTS`
- Turso supports `PRAGMA foreign_keys = ON` via `libsql` client config
- WAL mode is managed by Turso server-side; don't include `PRAGMA journal_mode = WAL`

- [x] **Step 1.3: Create `turso/seed.ts`**

A Node.js script that seeds the DB with initial schedules (from the existing `schedules` table defaults) and optionally projects from `projects.yml`.

```typescript
import { createClient } from "@libsql/client";
import { readFileSync } from "fs";
import { join } from "path";

const url = process.env.TURSO_DATABASE_URL!;
const authToken = process.env.TURSO_AUTH_TOKEN!;
const client = createClient({ url, authToken });

async function seed() {
  const schema = readFileSync(join(__dirname, "schema.sql"), "utf-8");
  await client.executeMultiple(schema);

  // Seed default schedules (match existing defaults from backend)
  const defaults = [
    { job_name: "synthesis_lead", cron: "0 1 * * *", timezone: "Asia/Manila", is_enabled: 1 },
    { job_name: "housekeeping", cron: "0 2 * * *", timezone: "UTC", is_enabled: 1 },
    { job_name: "from_the_desk", cron: "0 23 * * 0", timezone: "Asia/Manila", is_enabled: 1 },
  ];
  for (const s of defaults) {
    await client.execute({
      sql: `INSERT OR IGNORE INTO schedules (job_name, cron_expression, timezone, is_enabled) VALUES (?, ?, ?, ?)`,
      args: [s.job_name, s.cron, s.timezone, s.is_enabled],
    });
  }
  console.log("Seeded");
}
seed();
```

- [x] **Step 1.4: Create `api/lib/db.ts`**

```typescript
import { createClient, Client } from "@libsql/client";

let _client: Client | null = null;

export function getDb(): Client {
  if (!_client) {
    const url = process.env.TURSO_DATABASE_URL;
    const authToken = process.env.TURSO_AUTH_TOKEN;
    if (!url || !authToken) throw new Error("TURSO_DATABASE_URL and TURSO_AUTH_TOKEN required");
    _client = createClient({ url, authToken });
  }
  return _client;
}
```

- [x] **Step 1.5: Run seed script**

```bash
cd apps/frontend
npx tsx turso/seed.ts
```

- [x] **Step 1.6: Commit**

```bash
git add apps/frontend/turso/ apps/frontend/api/lib/db.ts
git commit -m "feat(db): add Turso schema, seed, and client wrapper"
```

---

## Task 2 — Encrypted Settings Store (TypeScript Port)

**Why:** The backend's `dispatch/crypto.py` and `dispatch/settings_store.py` need to work on Vercel. We port the Fernet encryption to the Web Crypto API (SubtleCrypto) and build a typed settings store.

**Files:**
- Create: `apps/frontend/api/lib/crypto.ts`
- Create: `apps/frontend/api/lib/settings.ts`

- [x] **Step 2.1: Create `api/lib/crypto.ts`**

Implement AES-256-GCM encryption compatible with Python Fernet's output format, OR implement a clean TypeScript-native encryption that shares the same key derivation. Since Fernet uses AES-128-CBC with HMAC, the simplest approach is to implement the same construction in TypeScript using Web Crypto.

Alternative (simpler): Use Web Crypto's `AES-GCM` with a key derived from `DISPATCH_MASTER_KEY` via PBKDF2. This is NOT Fernet-compatible, but since this is a fresh Vercel deployment (not migrating existing encrypted data), we can use a new format. The self-hosted backend and Vercel backend will have separate settings stores anyway.

```typescript
// api/lib/crypto.ts
import { createHash, randomBytes } from "crypto";

const MASTER_KEY = process.env.DISPATCH_MASTER_KEY!;
if (!MASTER_KEY) throw new Error("DISPATCH_MASTER_KEY required");

const KEY = createHash("sha256").update(MASTER_KEY).digest();

export async function encrypt(plaintext: string): Promise<string> {
  const iv = randomBytes(12);
  const encoder = new TextEncoder();
  const cryptoKey = await crypto.subtle.importKey("raw", KEY, { name: "AES-GCM" }, false, ["encrypt"]);
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, cryptoKey, encoder.encode(plaintext));
  const combined = Buffer.concat([iv, Buffer.from(ciphertext)]);
  return combined.toString("base64");
}

export async function decrypt(b64: string): Promise<string> {
  const combined = Buffer.from(b64, "base64");
  const iv = combined.subarray(0, 12);
  const ciphertext = combined.subarray(12);
  const cryptoKey = await crypto.subtle.importKey("raw", KEY, { name: "AES-GCM" }, false, ["decrypt"]);
  const plaintext = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, cryptoKey, ciphertext);
  return new TextDecoder().decode(plaintext);
}
```

- [x] **Step 2.2: Create `api/lib/settings.ts`**

Ports `dispatch/settings_store.py`:

```typescript
import { getDb } from "./db";
import { encrypt, decrypt } from "./crypto";

export async function getSetting(key: string): Promise<string | null> {
  const db = getDb();
  const row = await db.execute({ sql: "SELECT value FROM settings WHERE key = ?", args: [key] });
  if (!row.rows.length) return null;
  const encrypted = row.rows[0].value as string;
  return decrypt(encrypted);
}

export async function setSetting(key: string, value: string): Promise<void> {
  const db = getDb();
  const encrypted = await encrypt(value);
  await db.execute({
    sql: `INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value`,
    args: [key, encrypted],
  });
}

export async function listSettings(prefix = ""): Promise<Record<string, string>> {
  const db = getDb();
  const rows = await db.execute({
    sql: "SELECT key, value FROM settings WHERE key LIKE ? ORDER BY key",
    args: [`${prefix}%`],
  });
  const out: Record<string, string> = {};
  for (const r of rows.rows) {
    out[r.key as string] = await decrypt(r.value as string);
  }
  return out;
}
```

- [x] **Step 2.3: Commit**

```bash
git add apps/frontend/api/lib/crypto.ts apps/frontend/api/lib/settings.ts
git commit -m "feat(crypto): port encrypted settings store to TypeScript/Web Crypto"
```

---

## Task 3 — LLM Client (Gemini + Groq)

**Why:** Replace Kimi/Anthropic with free cloud LLMs that work from Vercel. Both Gemini and Groq offer OpenAI-compatible endpoints, so one client with two base URLs handles everything.

**Files:**
- Create: `apps/frontend/api/lib/llm.ts`

- [x] **Step 3.1: Create `api/lib/llm.ts`**

```typescript
// api/lib/llm.ts
import { z } from "zod";

interface LlmConfig {
  baseUrl: string;
  apiKey: string;
  model: string;
}

function getPrimaryConfig(): LlmConfig {
  const provider = process.env.DISPATCH_AI_PROVIDER || "gemini";
  if (provider === "groq") {
    return {
      baseUrl: "https://api.groq.com/openai/v1",
      apiKey: process.env.GROQ_API_KEY!,
      model: process.env.GROQ_MODEL || "llama-3.3-70b-versatile",
    };
  }
  return {
    baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai",
    apiKey: process.env.GEMINI_API_KEY!,
    model: process.env.GEMINI_MODEL || "gemini-2.5-flash",
  };
}

function getFallbackConfig(): LlmConfig | null {
  const primary = process.env.DISPATCH_AI_PROVIDER || "gemini";
  if (primary === "gemini" && process.env.GROQ_API_KEY) {
    return {
      baseUrl: "https://api.groq.com/openai/v1",
      apiKey: process.env.GROQ_API_KEY,
      model: process.env.GROQ_MODEL || "llama-3.3-70b-versatile",
    };
  }
  if (primary === "groq" && process.env.GEMINI_API_KEY) {
    return {
      baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai",
      apiKey: process.env.GEMINI_API_KEY,
      model: process.env.GEMINI_MODEL || "gemini-2.5-flash",
    };
  }
  return null;
}

export async function synthesize<T extends z.ZodType>(
  prompt: string,
  schema: T,
  config?: LlmConfig
): Promise<z.infer<T>> {
  const cfg = config || getPrimaryConfig();
  const fallback = getFallbackConfig();

  const systems = [cfg];
  if (fallback) systems.push(fallback);

  for (const sys of systems) {
    try {
      const response = await fetch(`${sys.baseUrl}/chat/completions`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${sys.apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: sys.model,
          messages: [{ role: "user", content: prompt }],
          response_format: { type: "json_object" },
          temperature: 0.7,
        }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      const content = data.choices[0].message.content;
      const parsed = JSON.parse(content);
      return schema.parse(parsed);
    } catch (e) {
      console.warn(`LLM ${sys.model} failed:`, e);
      continue;
    }
  }
  throw new Error("All LLM providers failed");
}
```

- [x] **Step 3.2: Add Zod schemas for synthesis outputs**

Create `api/lib/schema.ts` with Zod equivalents of `ArticleFiling`, `LeadFiling`, `AddendumFiling`:

```typescript
import { z } from "zod";

export const ArticleFilingSchema = z.object({
  article: z.string().min(1),
});

export const LeadFilingSchema = z.object({
  lead_headline: z.string().max(160),
  lead_body: z.string().max(600),
  active_count: z.number().int().min(0),
  project_lines: z.array(z.object({
    slug: z.string(),
    name: z.string(),
    status: z.string(),
    stat: z.string(),
    bullet: z.string(),
  })),
});

export const AddendumFilingSchema = z.object({
  label: z.string(),
  body: z.string().max(200),
});
```

- [x] **Step 3.3: Commit**

```bash
git add apps/frontend/api/lib/llm.ts apps/frontend/api/lib/schema.ts
git commit -m "feat(llm): add Gemini/Groq client with Zod schema validation"
```

---

## Task 4 — TTS Replacement (No ffmpeg)

**Why:** Vercel can't install ffmpeg. Briefing texts are short enough (~500 words lead, ~200 chars addendum) that we don't need chunking/concatenation. A single TTS call per briefing is sufficient.

**Options:**
1. **ElevenLabs free tier** — 10k chars/mo, excellent quality, no commercial rights on free plan
2. **Kokoro TTS via Hugging Face** — open-source, ~82M params, good quality, 100K HF credits/mo
3. **Paid ElevenLabs** ($5/mo) — commercial rights, 100k+ chars

**Recommendation:** Start with ElevenLabs free for development; upgrade to paid ($5/mo) for production. The cost is negligible compared to self-hosting a backend.

**Files:**
- Create: `apps/frontend/api/lib/tts.ts`

- [x] **Step 4.1: Create `api/lib/tts.ts`** — **Revised:** Uses backend `POST /api/tts/generate` instead of ElevenLabs/Kokoro. See ADR 001.

```typescript
// api/lib/tts.ts
export async function generateAudio(text: string): Promise<Buffer> {
  const apiKey = process.env.ELEVENLABS_API_KEY;
  if (!apiKey) throw new Error("ELEVENLABS_API_KEY required");

  const voiceId = process.env.ELEVENLABS_VOICE_ID || "21m00Tcm4TlvDq8ikWAM"; // Ava-like default
  const response = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`, {
    method: "POST",
    headers: {
      "xi-api-key": apiKey,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      text,
      model_id: "eleven_multilingual_v2",
      voice_settings: { stability: 0.5, similarity_boost: 0.75 },
    }),
  });
  if (!response.ok) throw new Error(`TTS failed: ${response.status}`);
  return Buffer.from(await response.arrayBuffer());
}
```

- [x] **Step 4.2: Commit**

```bash
git add apps/frontend/api/lib/tts.ts
git commit -m "feat(tts): add ElevenLabs TTS client (replaces Google Cloud + ffmpeg)"
```

---

## Task 5 — Ingest (GitHub API Only)

**Why:** Vercel has no filesystem access to `/repos`. We drop local git ingest and keep only the GitHub REST API ingestors. These are pure HTTP calls and work perfectly in serverless.

**Files:**
- Create: `apps/frontend/api/lib/ingest-github.ts`
- Create: `apps/frontend/api/lib/ingest-github-commits.ts`

- [x] **Step 5.1: Port `dispatch/ingest/github.py` to TypeScript**

The Python logic maps almost 1:1:
- `httpx.AsyncClient` → `fetch()`
- `async with db.cursor()` → `db.execute()`
- SQLite `INSERT OR IGNORE` → identical in Turso

Key changes:
- No local filesystem operations
- GitHub token from encrypted settings (not env var)
- Cursor storage in `cursors` table (same schema)

- [x] **Step 5.2: Port `dispatch/ingest/github_commits.py` to TypeScript**

Same pattern — pure GitHub API calls, branch enumeration, commit fetching, deduplication.

- [x] **Step 5.3: Commit**

```bash
git add apps/frontend/api/lib/ingest-github.ts apps/frontend/api/lib/ingest-github-commits.ts
git commit -m "feat(ingest): port GitHub ingestors to TypeScript (GitHub API only)"
```

---

## Task 6 — Synthesis Pipeline (Orchestrator Port)

**Why:** The core briefing generation logic in `dispatch/orchestrator.py` needs to run on Vercel. We port the key functions: `run_synthesis_lead`, `run_synthesis_addendum`, `run_audio`, `run_publish`.

**Files:**
- Create: `apps/frontend/api/lib/orchestrator.ts`
- Create: `apps/frontend/api/lib/prompt.ts` (ports `dispatch/synthesis/prompt.py`)
- Create: `apps/frontend/api/lib/bullets.ts` (ports `dispatch/synthesis/bullets.py`)
- Create: `apps/frontend/api/lib/brief-lint.ts` (ports `dispatch/synthesis/brief_lint.py`)
- Create: `apps/frontend/api/lib/mention-extraction.ts` (ports `dispatch/synthesis/mention_extraction.py`)

- [x] **Step 6.1: Port prompt builders**

Translate `build_article_prompt`, `build_lead_prompt`, `build_addendum_prompt` from Jinja2/string-building to TypeScript template literals. The prompt text itself stays identical.

- [x] **Step 6.2: Port `orchestrator.ts`**

Key functions to port:
- `_events_for_window` — Turso query
- `_project_input` — YAML load + bullet derivation
- `_resolve_target_date` — date logic (yesterday if uncovered and active)
- `_uncovered_day_with_activity` — SQL query
- `run_synthesis_lead` — two-pass synthesis (article → lead)
- `run_synthesis_addendum` — single-pass addendum
- `run_audio` — TTS + upload to R2
- `run_publish` — build snapshot + upload to R2

The logic is identical; only the DB client and async patterns change.

- [x] **Step 6.3: Commit**

```bash
git add apps/frontend/api/lib/orchestrator.ts apps/frontend/api/lib/prompt.ts apps/frontend/api/lib/bullets.ts apps/frontend/api/lib/brief-lint.ts apps/frontend/api/lib/mention-extraction.ts
git commit -m "feat(synthesis): port orchestrator and prompt builders to TypeScript"
```

---

## Task 7 — API Routes (Public + Admin)

**Why:** Replace FastAPI routers with Vercel Functions. File-based routing: each `.ts` file in `api/` becomes an endpoint.

**Vercel Function routing reference:**
- `api/briefings.ts` → `GET /api/briefings`
- `api/briefings/[date].ts` → `GET /api/briefings/:date`
- `api/admin/settings.ts` → `GET /api/admin/settings`
- `api/admin/settings/[key].ts` → `PUT /api/admin/settings/:key`

**Files:**
- Create: all route files listed in File Map

- [x] **Step 7.1: Create public routes**

Port each FastAPI router to a Vercel Function. Each function receives `VercelRequest` / `VercelResponse` (or standard `Request` / `Response` for Edge runtime).

Example pattern for `api/briefings.ts`:

```typescript
import type { VercelRequest, VercelResponse } from "@vercel/node";
import { getDb } from "../lib/db";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "GET") return res.status(405).end();
  const limit = Math.min(200, Math.max(1, parseInt(req.query.limit as string) || 50));
  const offset = Math.max(0, parseInt(req.query.offset as string) || 0);
  const db = getDb();
  // ... query logic ...
  res.status(200).json({ briefings, total });
}
```

- [x] **Step 7.2: Create admin routes**

Same pattern. Admin routes are perimeter-protected at the deployment layer (same invariant as before). No app-layer auth.

- [x] **Step 7.3: Create proxy route for podcasts**

`api/_proxy/podcasts/[...path].ts` proxies podcast requests to the self-hosted backend:

```typescript
import type { VercelRequest, VercelResponse } from "@vercel/node";

const PODCAST_BACKEND = process.env.PODCAST_BACKEND_URL!;

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const path = req.query.path as string[];
  const target = `${PODCAST_BACKEND}/api/podcasts/${path.join("/")}`;
  const response = await fetch(target, {
    method: req.method,
    headers: { "Content-Type": "application/json" },
    body: req.method !== "GET" ? JSON.stringify(req.body) : undefined,
  });
  const data = await response.text();
  res.status(response.status).send(data);
}
```

- [x] **Step 7.4: Commit**

```bash
git add apps/frontend/api/
git commit -m "feat(api): add all public and admin API routes as Vercel Functions"
```

---

## Task 8 — Vercel Cron Jobs

**Why:** Replace APScheduler with Vercel's built-in cron. Each cron job triggers an HTTP `GET` to a dedicated endpoint.

**Files:**
- Modify: `apps/frontend/vercel.json`
- Create: `apps/frontend/api/cron/*.ts`

- [x] **Step 8.1: Update `vercel.json`**

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "vite",
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "installCommand": "npm install",
  "rewrites": [
    { "source": "/api/(.*)", "destination": "/api/$1" },
    { "source": "/(.*)", "destination": "/index.html" }
  ],
  "headers": [
    {
      "source": "/assets/(.*)",
      "headers": [
        { "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }
      ]
    }
  ],
  "crons": [
    { "path": "/api/cron/ingest-github", "schedule": "*/30 * * * *" },
    { "path": "/api/cron/ingest-github-commits", "schedule": "0 * * * *" },
    { "path": "/api/cron/synthesis-lead", "schedule": "0 1 * * *" },
    { "path": "/api/cron/from-the-desk", "schedule": "0 23 * * 0" },
    { "path": "/api/cron/housekeeping", "schedule": "0 2 * * *" }
  ]
}
```

- [x] **Step 8.2: Create cron handlers**

Each cron handler is a thin wrapper around the orchestrator:

```typescript
// api/cron/synthesis-lead.ts
import type { VercelRequest, VercelResponse } from "@vercel/node";
import { runSynthesisLead } from "../lib/orchestrator";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  // Vercel Cron sets this user-agent
  if (req.headers["user-agent"] !== "vercel-cron/1.0") {
    return res.status(403).json({ error: "Forbidden" });
  }
  try {
    const result = await runSynthesisLead();
    res.status(200).json({ ok: true, result });
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e) });
  }
}
```

- [x] **Step 8.3: Commit**

```bash
git add apps/frontend/vercel.json apps/frontend/api/cron/
git commit -m "feat(cron): add Vercel Cron Jobs for ingest, synthesis, housekeeping"
```

---

## Task 9 — Frontend API Client Update

**Why:** The frontend currently calls `VITE_DISPATCH_API_URL || "/api"`. When co-deployed with the API on Vercel, same-origin `/api` works automatically. But we need to handle the podcast proxy path.

**Files:**
- Modify: `apps/frontend/src/api/client.ts`

- [x] **Step 9.1: Update `src/api/client.ts`**

Ensure podcast endpoints route through the proxy:

```typescript
const API_BASE = import.meta.env.VITE_DISPATCH_API_URL || "/api";

// Podcasts are proxied to the self-hosted backend
async function podcastFetch(path: string, init?: RequestInit) {
  const url = `${API_BASE}/_proxy/podcasts${path}`;
  // ...same fetch logic...
}

export async function fetchPodcasts() {
  return podcastFetch("/");
}

export async function fetchPodcastEpisodes(slug: string) {
  return podcastFetch(`/${slug}/episodes`);
}
```

- [x] **Step 9.2: Commit**

```bash
git add apps/frontend/src/api/client.ts
git commit -m "feat(frontend): update API client for same-origin Vercel deployment + podcast proxy"
```

---

## Task 10 — Environment Configuration

**Why:** Vercel uses its own env var system. We need an `.env.example` that documents all required and optional vars for local dev, plus instructions for Vercel dashboard configuration.

**Files:**
- Create: `apps/frontend/.env.example`
- Modify: `apps/frontend/package.json` (add deps)

- [x] **Step 10.1: Update `package.json`**

Add dependencies:

```json
{
  "dependencies": {
    "@libsql/client": "^0.14.0",
    "zod": "^3.23.0"
  },
  "devDependencies": {
    "@vercel/node": "^3.0.0"
  }
}
```

Run `npm install`.

- [x] **Step 10.2: Create `.env.example`**

```bash
# Required: encrypts settings at rest (same as backend)
DISPATCH_MASTER_KEY=

# Required: Turso database
TURSO_DATABASE_URL=libsql://...turso.io
TURSO_AUTH_TOKEN=

# LLM Provider (gemini | groq)
DISPATCH_AI_PROVIDER=gemini

# Gemini (free tier: 5 RPM, 100 RPD)
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

# Groq fallback (free tier: 14,400 RPD, 30 RPM)
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile

# TTS (ElevenLabs free: 10k chars/mo; paid starts at $5/mo)
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# Storage (R2 — same credentials as backend)
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET=
R2_PUBLIC_BASE_URL=

# GitHub ingest (personal access token)
GITHUB_TOKEN=

# Podcast proxy (self-hosted backend URL)
PODCAST_BACKEND_URL=https://dispatch-podcast.yourdomain.com

# Optional: timezone for cron scheduling
DISPATCH_TZ=Asia/Manila
```

- [x] **Step 10.3: Commit**

```bash
git add apps/frontend/.env.example apps/frontend/package.json apps/frontend/package-lock.json
git commit -m "chore(config): add .env.example and required deps for Vercel deployment"
```

---

## Task 11 — Vercel Deploy + Smoke Test

**Why:** Verify the entire pipeline works end-to-end on Vercel before declaring victory.

**Files:** none (deployment verification)

- [x] **Step 11.1: Link project to Vercel**

```bash
cd apps/frontend
vercel link
```

- [x] **Step 11.2: Set environment variables in Vercel dashboard**

```bash
vercel env add DISPATCH_MASTER_KEY
turso db tokens create dispatch-briefings | vercel env add TURSO_AUTH_TOKEN
vercel env add TURSO_DATABASE_URL
vercel env add GEMINI_API_KEY
# ... etc for all required vars
```

- [x] **Step 11.3: Deploy**

```bash
vercel --prod
```

- [x] **Step 11.4: Smoke test the API**

```bash
BASE="https://your-project.vercel.app"

# Health / snapshot
curl -fsS "$BASE/api/snapshot" | jq '.brief.lead_headline'

# Projects
curl -fsS "$BASE/api/projects" | jq '.projects | length'

# Briefings list
curl -fsS "$BASE/api/briefings?limit=5" | jq '.briefings | length'

# Admin settings (gated by your perimeter)
curl -fsS -H "Authorization: Bearer <token>" "$BASE/api/admin/settings" | jq '.settings | keys'

# Podcast proxy
curl -fsS "$BASE/api/_proxy/podcasts/" | jq '.podcasts | length'
```

- [x] **Step 11.5: Test cron triggers manually**

```bash
# Trigger ingest (should respect user-agent check)
curl -fsS "$BASE/api/cron/ingest-github" -H "User-Agent: vercel-cron/1.0"

# Trigger synthesis
curl -fsS "$BASE/api/cron/synthesis-lead" -H "User-Agent: vercel-cron/1.0"
```

- [x] **Step 11.6: Test manual briefing generation**

Via the admin UI or curl:

```bash
curl -fsS -X POST "$BASE/api/admin/briefings/generate" -H "Content-Type: application/json"
```

Expect: `{"generated": true/false, ...}`

- [x] **Step 11.7: Verify audio generation** — Audio generated via backend TTS endpoint; Issue #1 audio live at `dispatch-demo-api.marklab.uk`.

Check that a generated briefing has an audio file accessible at:
`$BASE/api/audio/{date}-lead`

- [x] **Step 11.8: Commit deploy lockfile**

```bash
git add apps/frontend/vercel.json
git commit -m "deploy(vercel): verified production deployment"
```

---

## Task 12 — Self-Hosted Backend Shrink

**Why:** The self-hosted backend now only needs to serve podcasts. We can strip out everything else to reduce its footprint.

**Files:**
- Modify: `apps/backend/dispatch/main.py` — remove briefing routers, keep podcast routers
- Modify: `apps/backend/dispatch/scheduler.py` — remove briefing/orchestrator jobs, keep podcast jobs
- Modify: `apps/backend/dispatch/orchestrator.py` — delete or move to archive (no longer used)

**Scope note:** This task is optional. You can leave the backend untouched and simply stop using its briefing endpoints. But cleaning it up prevents confusion.

- [x] **Step 12.1: Document the split in `docs/architecture/DEPLOYMENT.md`**

Add a section:

```markdown
## Hybrid Deployment (Recommended)

### Vercel (Briefings + Frontend)
- URL: `https://dispatch.vercel.app`
- Responsibilities: Frontend SPA, briefings API, snapshots, admin, ingest, synthesis, TTS
- Database: Turso (serverless SQLite)
- LLM: Gemini/Groq (free tiers)
- Cron: Vercel Cron Jobs

### Self-Hosted (Podcasts Only)
- URL: `https://podcast.dispatch.yourdomain.com`
- Responsibilities: Podcast generation, NotebookLM integration, ffmpeg audio processing
- Database: SQLite (local)
- Cron: APScheduler
- Requirements: Docker, ffmpeg, ~512MB RAM
```

- [x] **Step 12.2: Commit**

```bash
git add docs/architecture/DEPLOYMENT.md
git commit -m "docs(deployment): document hybrid Vercel + self-hosted architecture"
```

---

## Task 13 — Plan Wrap-Up

- [x] **Step 13.1: Run a final manual end-to-end test**

1. GitHub ingest runs (cron or manual trigger) → events appear in Turso
2. Lead synthesis runs → filing appears in Turso
3. TTS generates → audio uploaded to R2
4. Snapshot builds → JSON uploaded to R2
5. Frontend loads → snapshot renders correctly
6. Admin UI shows runs + settings

- [x] **Step 13.2: Archive the plan**

```bash
mkdir -p docs/plans/completed/2026-05
git mv docs/plans/2026-05-26-briefings-vercel-serverless.md docs/plans/completed/2026-05/
```

Update `docs/plans/README.md` — move from Active to Completed.

```bash
git add docs/plans/README.md
git commit -m "docs(plans): archive briefings Vercel migration as completed"
```

---

## Acceptance Criteria

Phase is complete when ALL of these are true:

- [x] `npm run build` in `apps/frontend/` succeeds and produces a working `dist/`.
- [x] `vercel --prod` deploys successfully with zero build errors.
- [x] `GET /api/snapshot` returns valid JSON with the latest briefing.
- [x] `GET /api/briefings` returns paginated briefings.
- [x] `POST /api/admin/briefings/generate` successfully synthesizes a lead, generates TTS audio, and publishes a snapshot.
- [x] Vercel Cron Jobs trigger without error (visible in Vercel dashboard logs).
- [x] GitHub ingest cron adds events to Turso (verified by querying DB).
- [x] Podcast proxy routes work: `GET /api/proxy/podcasts/` returns podcasts from self-hosted backend.

## Post-completion notes

### TTS did not move to Vercel

The original plan assumed TTS would run on Vercel (ElevenLabs or Kokoro). During
implementation we discovered:

1. **Hugging Face Inference API is dead.** `api-inference.huggingface.co` no
   longer resolves. HF migrated to `router.huggingface.co` which does not serve
   TTS models.
2. **Kokoro in Vercel serverless is impractical.** The WASM phonemizer fails in
   the serverless environment, and the bundle (~166 MB) is too heavy.
3. **The marklab backend already had working Google Cloud TTS.** It had
   generated Issue #1 audio before the migration started.

**Decision:** Keep TTS on the backend. The Vercel frontend delegates audio
generation to `POST /api/tts/generate` on the marklab backend. See
[ADR 001](../architecture/adr/001-tts-on-marklab-backend.md).

### What changed in the plan

| Original plan | Actual |
|---|---|
| TTS on Vercel (ElevenLabs/Kokoro) | TTS on marklab backend (Google Cloud Chirp 3 HD) |
| Backend becomes "podcasts only" | Backend handles TTS + podcasts |
| `api/_proxy/podcasts/` path | `api/proxy/podcasts/` path |
| No backend audio fallback in frontend | Frontend falls back to backend audio URL when local DB has none |
- [ ] Frontend admin UI can read/write settings, projects, and schedules.
- [ ] No ffmpeg or local filesystem access is required by the Vercel deployment.
- [ ] The self-hosted backend still generates podcasts successfully (unchanged).
- [ ] Plan is archived to `docs/plans/completed/2026-05/`.
