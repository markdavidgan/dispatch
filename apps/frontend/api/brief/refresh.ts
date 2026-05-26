import type { VercelRequest, VercelResponse } from "@vercel/node";
import { runSynthesisAddendum, runAudio, runPublish } from "../../_lib/orchestrator";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "POST") return res.status(405).end();
  try {
    const addendum = await runSynthesisAddendum();
    const text = `${addendum.label}. ${addendum.body}`;
    let audio = null;
    try {
      audio = await runAudio("addendum", undefined, text);
    } catch (e) {
      console.warn("audio non-fatal failure:", e);
    }
    const { url } = await runPublish();
    res.status(200).json({ ok: true, addendum, snapshot_url: url, audio });
  } catch (e) {
    res.status(503).json({ ok: false, error: String(e) });
  }
}
