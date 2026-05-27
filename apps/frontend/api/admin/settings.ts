import type { VercelRequest, VercelResponse } from "@vercel/node";
import { listSettings } from "../_lib/settings.js";
import { ensureSchema } from "../_lib/db.js";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "GET") return res.status(405).end();
  await ensureSchema();
  const prefix = (req.query.prefix as string) || "";
  const settingsMap = await listSettings(prefix);
  const settings = Object.entries(settingsMap).map(([key, value]) => ({ key, value }));
  res.status(200).json({ settings });
}
