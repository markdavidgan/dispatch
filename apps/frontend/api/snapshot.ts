import type { VercelRequest, VercelResponse } from "@vercel/node";
import { buildSnapshot } from "./lib/snapshot";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "GET") return res.status(405).end();
  try {
    const snapshot = await buildSnapshot();
    res.status(200).json(snapshot);
  } catch (e) {
    res.status(500).json({ error: String(e) });
  }
}
