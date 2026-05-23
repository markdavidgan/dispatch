/**
 * Briefings archive fetch helpers.
 *
 * Talks to the collector API. Service-token headers are optional;
 * the standalone backend accepts requests directly or via its own auth.
 *
 * Runs server-side only.
 */

const API_URL = process.env.DISPATCH_API_URL || "http://localhost:10060";

/**
 * Backend emits absolute R2 URLs ({R2_PUBLIC_BASE_URL}/dispatch/audio/...)
 * but the bucket isn't publicly readable, so those URLs don't play in
 * browsers. Rewrite them to our /api/audio/[...key] proxy, which streams
 * through the CF-Access-gated frontend with server-side R2 credentials.
 */
function rewriteAudioUrl(url: string | null): string | null {
  if (!url) return null;
  // Match "/dispatch/audio/..." or "/podcast/..." from any host and rewrite.
  const m = url.match(/\/(dispatch\/audio\/[^?#]+|podcast\/[^?#]+)$/);
  if (!m) return url;
  return `/api/audio/${m[1]}`;
}

export interface BriefingSummary {
  date: string; // YYYY-MM-DD
  issue_no: number;
  lead_headline: string;
  audio_url: string | null;
  active_count: number;
  filed_at: string; // "02:00"
}

export interface BriefingDetail extends BriefingSummary {
  lead_body: string;
  lead_article?: string;
  addendums: { filed_at: string; label: string; body: string }[];
  projects: {
    slug: string;
    name: string;
    status: string;
    bullet: string;
    stat: string;
    kind: string | null;
  }[];
  audio_lead_url: string | null;
  audio_addendum_url: string | null;
  recent_events: {
    project_slug: string;
    kind: string;
    external_id: string;
    title: string;
    occurred_at: string | null;
    url: string | null;
  }[];
}

function cfHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const id = process.env.CF_ACCESS_CLIENT_ID;
  const sec = process.env.CF_ACCESS_CLIENT_SECRET;
  if (id && sec) {
    headers["CF-Access-Client-Id"] = id;
    headers["CF-Access-Client-Secret"] = sec;
  }
  return headers;
}

export async function fetchBriefings(): Promise<BriefingSummary[]> {
  const headers = cfHeaders();
  try {
    const r = await fetch(`${API_URL}/briefings?limit=50&offset=0`, { headers, next: { revalidate: 300 } });
    if (!r.ok) return [];
    const data = await r.json();
    const briefings: BriefingSummary[] = data.briefings ?? [];
    return briefings.map((b) => ({ ...b, audio_url: rewriteAudioUrl(b.audio_url) }));
  } catch {
    return [];
  }
}

export async function fetchBriefing(date: string): Promise<BriefingDetail | null> {
  const headers = cfHeaders();
  try {
    // Past briefings are effectively immutable once filed; 24h ISR is
    // appropriate. Today's briefing date is bounded by the route-level
    // revalidate=300 in `app/briefings/[date]/page.tsx`.
    const r = await fetch(`${API_URL}/briefings/${date}`, { headers, next: { revalidate: 86400 } });
    if (!r.ok) return null;
    const detail: BriefingDetail = await r.json();
    return {
      ...detail,
      audio_url: rewriteAudioUrl(detail.audio_url),
      audio_lead_url: rewriteAudioUrl(detail.audio_lead_url),
      audio_addendum_url: rewriteAudioUrl(detail.audio_addendum_url),
    };
  } catch {
    return null;
  }
}
