import type { VercelRequest, VercelResponse } from "@vercel/node";
import { setSetting } from "../../_lib/settings.js";
import { ensureSchema } from "../../_lib/db.js";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "POST") return res.status(405).end();
  await ensureSchema();
  const body = req.body || {};
  const settings = body.settings || {};
  for (const [key, value] of Object.entries(settings)) {
    await setSetting(key, value as string);
  }
  res.status(200).json({ updated: Object.keys(settings) });
}
