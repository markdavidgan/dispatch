import type { VercelRequest, VercelResponse } from "@vercel/node";
import { runSynthesisLead, runAudio, runPublish } from "../../_lib/orchestrator.js";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "POST") return res.status(405).end();
  const body = req.body || {};
  const targetDate = body.date as string | undefined;

  try {
    const lead = await runSynthesisLead(targetDate);
    if (lead.skipped) {
      return res.status(200).json({ generated: false, reason: lead.reason });
    }

    let audio = null;
    try {
      audio = await runAudio("lead", lead.date as string);
    } catch (e) {
      console.warn("audio non-fatal:", e);
    }

    const { url } = await runPublish();
    return res.status(200).json({ generated: true, lead, audio, snapshot_url: url });
  } catch (e) {
    res.status(503).json({ error: String(e) });
  }
}
