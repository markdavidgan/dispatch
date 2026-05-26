import type { VercelRequest, VercelResponse } from "@vercel/node";
import { runSynthesisLead, runAudio, runPublish } from "../../../_lib/orchestrator";
import { findLatestUncoveredDayWithActivity } from "../../../_lib/orchestrator";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "POST") return res.status(405).end();

  try {
    const target = await findLatestUncoveredDayWithActivity(30);
    if (!target) {
      return res.status(200).json({ generated: false, reason: "no uncovered day with activity in the last 30 days" });
    }

    const lead = await runSynthesisLead(target);
    if (lead.skipped) {
      return res.status(200).json({ generated: false, date: target, reason: lead.reason });
    }

    let audio = null;
    try {
      audio = await runAudio("lead", lead.date as string);
    } catch (e) {
      console.warn("audio non-fatal:", e);
    }

    const { url } = await runPublish();
    res.status(200).json({
      generated: true,
      kind: "lead",
      date: lead.date,
      issue_no: lead.issue_no,
      headline: lead.headline,
      snapshot_url: url,
      audio,
    });
  } catch (e) {
    res.status(503).json({ error: String(e) });
  }
}
