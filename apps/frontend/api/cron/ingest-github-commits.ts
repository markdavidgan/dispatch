import type { VercelRequest, VercelResponse } from "@vercel/node";
import { runIngestGitHubCommits } from "../_lib/orchestrator.js";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.headers["user-agent"] !== "vercel-cron/1.0") {
    return res.status(403).json({ error: "Forbidden" });
  }
  try {
    const total = await runIngestGitHubCommits();
    res.status(200).json({ ok: true, events_added: total });
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e) });
  }
}
