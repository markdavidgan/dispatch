import type { VercelRequest, VercelResponse } from "@vercel/node";
import { runAudio, runPublish } from "../../_lib/orchestrator.js";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "POST") return res.status(405).end();

  const body = req.body || {};
  const kind = (body.kind as "lead" | "addendum") || "lead";
  const date = body.date as string | undefined;
  const text = body.text as string | undefined;

  try {
    const audio = await runAudio(kind, date, text);
    const { url } = await runPublish();
    res.status(200).json({ ok: true, audio, snapshot_url: url });
  } catch (e) {
    res.status(503).json({ ok: false, error: String(e) });
  }
}
