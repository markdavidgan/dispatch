import type { VercelRequest, VercelResponse } from "@vercel/node";
import { runSynthesisLead } from "../../../lib/orchestrator";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "POST") return res.status(405).end();
  const body = req.body || {};
  const targetDate = body.date as string | undefined;

  try {
    const lead = await runSynthesisLead(targetDate);
    if (lead.skipped) {
      return res.status(200).json({ generated: false, reason: lead.reason });
    }
    return res.status(200).json({ generated: true, lead });
  } catch (e) {
    res.status(503).json({ error: String(e) });
  }
}
