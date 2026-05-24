const API_BASE = import.meta.env.VITE_DISPATCH_API_URL || "/api";

async function apiFetch(path: string, init?: RequestInit) {
  const url = `${API_BASE}${path}`;
  const resp = await fetch(url, {
    ...init,
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
  return apiFetch(`/briefings/${date}`);
}

// Projects
export async function fetchProjects() {
  return apiFetch("/projects");
}

// Podcasts
export async function fetchPodcasts() {
  return apiFetch("/podcasts");
}

export async function fetchPodcastEpisodes(slug: string) {
  return apiFetch(`/podcasts/${slug}/episodes`);
}

// Audio
export function audioUrl(key: string) {
  return `${API_BASE}/audio/${key}`;
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
export async function listAdminProjects() {
  return apiFetch("/admin/projects");
}

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
  return apiFetch("/admin/system/setup-status");
}

export async function triggerBackup() {
  return apiFetch("/admin/system/backup-now", { method: "POST" });
}

// Refresh briefing
export async function refreshBriefing() {
  return apiFetch("/brief/refresh", { method: "POST" });
}
