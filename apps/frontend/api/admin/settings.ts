import type { VercelRequest, VercelResponse } from "@vercel/node";
import { listSettings } from "../../_lib/settings.js";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "GET") return res.status(405).end();
  const prefix = (req.query.prefix as string) || "";
  const settings = await listSettings(prefix);
  res.status(200).json({ settings });
}
