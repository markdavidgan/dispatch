/**
 * Server-only helper to fetch live data from the collector.
 *
 * This runs inside server components and route handlers only.
 */

const API_URL = process.env.DISPATCH_API_URL || "http://localhost:10060";

export interface LiveProject {
  open_prs: number;
  commits_7d: number;
  last_commit_at: string | null;
}

export interface LiveData {
  as_of: string;
  projects: Record<string, LiveProject>;
}

export async function fetchLive(): Promise<LiveData | null> {
  const headers: Record<string, string> = {};
  const clientId = process.env.CF_ACCESS_CLIENT_ID;
  const clientSecret = process.env.CF_ACCESS_CLIENT_SECRET;
  if (clientId && clientSecret) {
    headers["CF-Access-Client-Id"] = clientId;
    headers["CF-Access-Client-Secret"] = clientSecret;
  }

  try {
    const res = await fetch(`${API_URL}/live`, {
      headers,
      next: { revalidate: 60 }, // 1 min
    });
    if (!res.ok) {
      console.warn("live fetch failed", res.status);
      return null;
    }
    return (await res.json()) as LiveData;
  } catch (e) {
    console.error("fetchLive failed", e);
    return null;
  }
}
