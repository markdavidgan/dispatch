export const IS_DEMO = false;

const API_BASE = "/api";

async function apiFetch(path: string, init?: RequestInit) {
  const url = `${API_BASE}${path}`;
  const resp = await fetch(url, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`API ${path} failed: ${resp.status} ${text}`);
  }
  return resp.json();
}

// Snapshot
export async function fetchSnapshot() {
  return apiFetch("/snapshot");
}

// Live stats
export async function fetchLive() {
  return apiFetch("/live");
}

// Briefings
export async function fetchBriefings(limit = 50, offset = 0) {
  return apiFetch(`/briefings?limit=${limit}&offset=${offset}`);
}

export async function fetchBriefing(date: string) {
  return apiFetch(`/briefings/${encodeURIComponent(date)}`);
}

// Projects
export async function fetchProjects() {
  return apiFetch("/projects");
}

// Podcasts (proxied to self-hosted backend)
async function podcastFetch(path: string, init?: RequestInit) {
  const url = `${API_BASE}/proxy/podcasts?path=${encodeURIComponent(path)}`;
  const resp = await fetch(url, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Podcast API ${path} failed: ${resp.status} ${text}`);
  }
  return resp.json();
}

export async function fetchPodcasts() {
  return podcastFetch("/");
}

export async function fetchPodcastEpisodes(slug: string) {
  return podcastFetch(`/${slug}/episodes`);
}

// Audio
export function audioUrl(key: string) {
  return `${API_BASE}/audio?key=${encodeURIComponent(key)}`;
}

// Admin — Settings
export async function listSettings(prefix = "") {
  return apiFetch(`/admin/settings?prefix=${encodeURIComponent(prefix)}`);
}

export async function putSetting(key: string, value: string) {
  return apiFetch(`/admin/settings/${key}`, {
    method: "PUT",
    body: JSON.stringify({ key, value }),
  });
}

export async function bulkUpdateSettings(settings: Record<string, string>) {
  return apiFetch("/admin/settings/bulk", {
    method: "POST",
    body: JSON.stringify({ settings }),
  });
}

// Admin — Projects
export async function createAdminProject(body: object) {
  return apiFetch("/admin/projects", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateAdminProject(slug: string, body: object) {
  return apiFetch(`/admin/projects/${slug}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteAdminProject(slug: string) {
  return apiFetch(`/admin/projects/${slug}`, { method: "DELETE" });
}

// Admin — Schedules
export async function listSchedules() {
  return apiFetch("/admin/schedules");
}

export async function updateSchedule(jobName: string, body: object) {
  return apiFetch(`/admin/schedules/${jobName}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

// Admin — Runs
export async function listRuns(params = "") {
  return apiFetch(`/admin/runs${params}`);
}

// Admin — System
export async function fetchSetupStatus() {
  return apiFetch("/proxy/setup-status");
}

export async function triggerBackup() {
  return apiFetch("/admin/system/backup-now", { method: "POST" });
}

// Refresh briefing (legacy public endpoint — addendum only)
export async function refreshBriefing() {
  return apiFetch("/brief/refresh", { method: "POST" });
}

// Admin — Generate briefing (lead if none exists, addendum if lead exists)
export async function generateBriefing() {
  return apiFetch("/admin/briefings/generate", { method: "POST" });
}
