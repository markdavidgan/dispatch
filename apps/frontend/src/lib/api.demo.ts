/**
 * Demo-mode API wrapper.
 *
 * Mirrors the exports of `api.ts` but reads from static JSON files baked into
 * the build at `/demo-data/`. Used only for static demo deployments;
 * self-hosted instances continue to use the real `api.ts`.
 *
 * To build a demo:
 *   npm run build:demo
 *
 * This swaps `@/lib/api` to this module via `vite.demo.config.ts`.
 */

export const IS_DEMO = true;

const DEMO_BASE = "/demo-data";

async function demoFetch(path: string): Promise<unknown> {
  const cleanPath = path.split("?")[0];
  const resp = await fetch(`${DEMO_BASE}${cleanPath}.json`);
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Demo data ${cleanPath} failed: ${resp.status} ${text}`);
  }
  return resp.json();
}

/* ── Public / reader API ── */

export async function fetchSnapshot() {
  return demoFetch("/snapshot");
}

export async function fetchLive() {
  return demoFetch("/live");
}

export async function fetchBriefings() {
  return demoFetch("/briefings");
}

export async function fetchBriefing(date: string) {
  return demoFetch(`/briefings/${encodeURIComponent(date)}`);
}

export async function fetchProjects() {
  return demoFetch("/projects");
}

export async function fetchPodcasts() {
  return demoFetch("/podcasts");
}

export async function fetchPodcastEpisodes(slug: string) {
  return demoFetch(`/podcast-${encodeURIComponent(slug)}-episodes`);
}

export function audioUrl(_key: string): string {
  // Demo builds do not include MP3 files; return an empty string so the
  // audio player renders its fallback state.
  return "";
}

/* ── Admin API (read-only / no-op) ── */

export async function listSettings(_prefix = "") {
  return { settings: {} };
}

export async function putSetting(_key: string, _value: string) {
  throw new Error("Demo mode — settings are read-only.");
}

export async function bulkUpdateSettings(_settings: Record<string, string>) {
  throw new Error("Demo mode — settings are read-only.");
}

export async function createAdminProject(_body: object) {
  throw new Error("Demo mode — projects are read-only.");
}

export async function updateAdminProject(_slug: string, _body: object) {
  throw new Error("Demo mode — projects are read-only.");
}

export async function deleteAdminProject(_slug: string) {
  throw new Error("Demo mode — projects are read-only.");
}

export async function listSchedules() {
  return { schedules: [] };
}

export async function updateSchedule(_jobName: string, _body: object) {
  throw new Error("Demo mode — schedules are read-only.");
}

export async function listRuns(_params = "") {
  return { runs: [], total: 0 };
}

export async function fetchSetupStatus() {
  return demoFetch("/setup-status");
}

export async function triggerBackup() {
  throw new Error("Demo mode — backup is not available.");
}

export async function refreshBriefing() {
  throw new Error("Demo mode — briefing generation is not available.");
}

export async function generateBriefing() {
  throw new Error("Demo mode — briefing generation is not available.");
}
