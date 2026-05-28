#!/usr/bin/env node
/**
 * Build script for static demo data.
 *
 * Fetches public data from a running Dispatch backend and writes static JSON
 * files to `public/demo-data/`. These files are then baked into the demo build
 * and served as static assets — no backend required at runtime.
 *
 * Usage:
 *   DEMO_API_BASE=http://127.0.0.1:10060/api npx tsx scripts/build-demo-data.ts
 *
 * The script is automatically invoked by `npm run build:demo`.
 */
import { mkdir, rm, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const API_BASE = (process.env.DEMO_API_BASE || "http://127.0.0.1:10060/api").replace(/\/$/, "");
const OUTDIR = join(__dirname, "..", "public", "demo-data");

async function fetchJson(path: string): Promise<unknown> {
  const url = `${API_BASE}${path}`;
  const resp = await fetch(url);
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Failed ${path}: ${resp.status} ${text}`);
  }
  return resp.json();
}

async function writeJson(name: string, data: unknown) {
  const path = join(OUTDIR, `${name}.json`);
  await writeFile(path, JSON.stringify(data, null, 2));
}

async function main() {
  console.log(`Fetching demo data from ${API_BASE} …`);

  // Clean and recreate output dir
  await rm(OUTDIR, { recursive: true, force: true });
  await mkdir(OUTDIR, { recursive: true });
  await mkdir(join(OUTDIR, "briefings"), { recursive: true });

  // Fetch public read-only data
  const snapshot = await fetchJson("/snapshot");
  const live = await fetchJson("/live");
  const briefingsList = (await fetchJson("/briefings?limit=20")) as { briefings: Array<{ date: string }> };
  const projects = await fetchJson("/projects");
  const podcasts = (await fetchJson("/proxy/podcasts?path=/")) as { podcasts: Array<{ project_slug: string }> };
  const setupStatus = await fetchJson("/proxy/setup-status");

  // Write top-level data
  await writeJson("snapshot", snapshot);
  await writeJson("live", live);
  await writeJson("briefings", briefingsList);
  await writeJson("projects", projects);
  await writeJson("podcasts", podcasts);
  await writeJson("setup-status", setupStatus);

  // Fetch individual briefing details
  for (const b of briefingsList.briefings || []) {
    const date = b.date;
    try {
      const detail = await fetchJson(`/briefings/${encodeURIComponent(date)}`);
      await writeJson(`briefings/${date}`, detail);
      console.log(`  ✓ briefing ${date}`);
    } catch (e) {
      console.warn(`  ⚠ skipping briefing ${date}: ${e}`);
    }
  }

  // Fetch podcast episodes
  for (const p of podcasts.podcasts || []) {
    const slug = p.project_slug;
    try {
      const episodes = await fetchJson(`/proxy/podcasts?path=/${encodeURIComponent(slug)}/episodes`);
      await writeJson(`podcast-${slug}-episodes`, episodes);
      console.log(`  ✓ podcast ${slug}`);
    } catch (e) {
      console.warn(`  ⚠ skipping podcast ${slug}: ${e}`);
    }
  }

  console.log(`\nDemo data written to ${OUTDIR}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
