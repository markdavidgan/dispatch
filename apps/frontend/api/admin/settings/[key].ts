import type { VercelRequest, VercelResponse } from "@vercel/node";
import { getSetting, setSetting } from "../../../lib/settings";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  const key = req.query.key as string;
  if (req.method === "GET") {
    const value = await getSetting(key);
    res.status(200).json({ key, value });
  } else if (req.method === "PUT") {
    const body = req.body || {};
    await setSetting(key, body.value || "");
    res.status(200).json({ key, value: body.value });
  } else {
    res.status(405).end();
  }
}
