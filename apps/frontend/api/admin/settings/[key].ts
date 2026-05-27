import type { VercelRequest, VercelResponse } from "@vercel/node";
import { getSetting, setSetting } from "../../_lib/settings.js";
import { ensureSchema } from "../../_lib/db.js";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const key = req.query.key as string;
  await ensureSchema();
  if (req.method === "GET") {
    try {
      const value = await getSetting(key);
      res.status(200).json({ key, value });
    } catch (e: any) {
      if (e.message?.includes("DISPATCH_MASTER_KEY")) {
        return res.status(503).json({ error: "DISPATCH_MASTER_KEY not configured", key, value: null });
      }
      throw e;
    }
  } else if (req.method === "PUT") {
    const body = req.body || {};
    await setSetting(key, body.value || "");
    res.status(200).json({ key, value: body.value });
  } else {
    res.status(405).end();
  }
}
