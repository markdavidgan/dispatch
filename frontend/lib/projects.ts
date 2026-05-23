/**
 * Server-side helper to fetch the project registry from the collector.
 *
 * Used as a fallback by per-project pages when the R2 snapshot doesn't
 * exist yet (pre-first-synthesis lifetime). Calls /projects on the
 * private API via Cloudflare Access service token.
 */

const API_URL = process.env.DISPATCH_API_URL || "http://localhost:10060";

export interface RegistryProject {
  slug: string;
  display_name: string;
  status: "active" | "held" | "archived";
  kind: string | null;
  color_hint: string | null;
  github_repo: string | null;
  local_path: string | null;
}

export async function fetchProjects(): Promise<RegistryProject[] | null> {
  try {
    const headers: Record<string, string> = {};
    const clientId = process.env.CF_ACCESS_CLIENT_ID;
    const clientSecret = process.env.CF_ACCESS_CLIENT_SECRET;
    if (clientId && clientSecret) {
      headers["Cf-Access-Client-Id"] = clientId;
      headers["Cf-Access-Client-Secret"] = clientSecret;
    }
    const res = await fetch(`${API_URL}/projects`, {
      headers,
      next: { revalidate: 60 },
    });
    if (!res.ok) {
      console.warn("fetchProjects returned", res.status);
      return null;
    }
    return (await res.json()) as RegistryProject[];
  } catch (e) {
    console.error("fetchProjects failed", e);
    return null;
  }
}
