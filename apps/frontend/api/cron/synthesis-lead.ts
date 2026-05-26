import type { VercelRequest, VercelResponse } from "@vercel/node";
import { runSynthesisLead, runAudio, runPublish } from "../../_lib/orchestrator.js";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.headers["user-agent"] !== "vercel-cron/1.0") {
    return res.status(403).json({ error: "Forbidden" });
  }
  try {
    const lead = await runSynthesisLead();
    if (lead.skipped) {
      return res.status(200).json({ ok: true, skipped: true, reason: lead.reason });
    }
    try {
      await runAudio("lead", lead.date as string);
    } catch (e) {
      console.warn("audio non-fatal:", e);
    }
    await runPublish();
    res.status(200).json({ ok: true, date: lead.date });
  } catch (e) {
    res.status(500).json({ ok: false, error: String(e) });
  }
}
