/**
 * Fetch the snapshot from R2 via Cloudflare's native REST API.
 *
 * Runs server-side only (RSC or route handlers). Never expose credentials
 * to the browser. Uses CLOUDFLARE_EMAIL + CLOUDFLARE_GLOBAL_API_KEY (already
 * in Doppler / Vercel env), not S3-compatible tokens — matches the pattern
 * used by aether-focus/tools/podcast/scripts/upload_to_r2.py and the design
 * revision in commit 54c4a04.
 */

const SNAPSHOT_KEY = "dispatch/snapshot.json";

function rewriteAudioUrl(url: string | null): string | null {
  if (!url) return null;
  const m = url.match(/\/(dispatch\/audio\/[^?#]+|podcast\/[^?#]+)$/);
  return m ? `/api/audio/${m[1]}` : url;
}

export interface ProjectLine {
  slug: string;
  name: string;
  status: "active" | "held";
  stat: string;
  bullet: "red" | "amber" | "sand";
  kind?: string | null;
}

export interface Addendum {
  filed_at: string;
  label: string;
  body: string;
}

export interface Brief {
  date: string;
  issue_no: number;
  filed_at: string;
  active_count: string;
  lead_headline: string;
  lead_body: string;
  projects: ProjectLine[];
  addendums: Addendum[];
  audio: {
    lead_url: string | null;
    lead_duration_s: number | null;
    addendum_url: string | null;
    addendum_duration_s: number | null;
    voice: string;
  } | null;
}

export interface BriefingMention {
  date: string; // YYYY-MM-DD
  excerpt: string;
  issue_no?: number | null;
}

export interface SnapshotProject {
  slug: string;
  name: string;
  status: string;
  kind: string | null;
  color_hint: string | null;
  // Optional Phase B fields — backend will populate. Frontend renders empty
  // states when null/undefined.
  summary?: string | null;
  from_the_desk?: string | null;
  from_the_desk_generated_at?: string | null;
  mentioned_in_briefings?: BriefingMention[];
}

export interface SnapshotEvent {
  project_slug: string;
  kind: string;
  external_id: string;
  title: string | null;
  author: string | null;
  occurred_at: string;
  url: string | null;
}

/**
 * Marginalia card on the home page uses a small subset of episode fields.
 * Keep `title` required (the snapshot always emits it) but allow
 * `episode_no` and `podcast_title` to be optional — the snapshot generator
 * may not always emit them in lockstep with the frontend.
 */
export interface SnapshotEpisode {
  episode_no?: number | null;
  podcast_title?: string;
  title: string;
}

export interface Snapshot {
  version: number;
  generated_at: string;
  brief: Brief | null;
  projects: SnapshotProject[];
  recent_events: SnapshotEvent[];
  episodes: SnapshotEpisode[];
  signature?: string;
}

// Read-time shim mirroring backend's _normalize_snapshot() in
// apps/backend/dispatch/publish/snapshot.py. Historical R2 snapshots written
// before the 2026-05-18 bureau→project rename still have `brief.bureaus`.
// Frontend reads R2 directly (bypassing the backend), so it needs its own
// normalization. Safe to remove once all historical snapshots have been
// regenerated (currently lazy via the next 02:00 cron or /brief/refresh).
function normalizeSnapshot(raw: unknown): Snapshot {
  const data = raw as Snapshot & { brief?: { bureaus?: ProjectLine[] } };
  if (data.brief && (data.brief as { bureaus?: unknown }).bureaus !== undefined
    && data.brief.projects === undefined) {
    data.brief.projects = (data.brief as { bureaus: ProjectLine[] }).bureaus;
    delete (data.brief as { bureaus?: unknown }).bureaus;
  }
  return data;
}

export async function fetchSnapshot(): Promise<Snapshot | null> {
  const accountId = process.env.CLOUDFLARE_ACCOUNT_ID;
  const bucket = process.env.R2_BUCKET_NAME;
  const email = process.env.CLOUDFLARE_EMAIL;
  const apiKey = process.env.CLOUDFLARE_GLOBAL_API_KEY;
  if (!accountId || !bucket || !email || !apiKey) {
    console.warn("fetchSnapshot: Cloudflare R2 creds not configured");
    return null;
  }
  const url = `https://api.cloudflare.com/client/v4/accounts/${accountId}/r2/buckets/${bucket}/objects/${SNAPSHOT_KEY}`;
  try {
    const res = await fetch(url, {
      headers: {
        "X-Auth-Email": email,
        "X-Auth-Key": apiKey,
      },
      next: { revalidate: 300 }, // 5 min ISR backstop
    });
    if (!res.ok) {
      if (res.status !== 404) {
        console.warn("snapshot fetch returned", res.status);
      }
      return null;
    }
    const raw = await res.json();
    const data: Snapshot = normalizeSnapshot(raw);
    if (!data.signature) {
      console.warn("snapshot missing signature");
    }
    // The snapshot's audio URLs are absolute R2 paths that won't play in
    // browsers (bucket isn't publicly readable). Rewrite to the proxy.
    if (data.brief?.audio) {
      data.brief.audio.lead_url = rewriteAudioUrl(data.brief.audio.lead_url);
      data.brief.audio.addendum_url = rewriteAudioUrl(data.brief.audio.addendum_url);
    }
    return data;
  } catch (e) {
    console.error("fetchSnapshot failed", e);
    return null;
  }
}
