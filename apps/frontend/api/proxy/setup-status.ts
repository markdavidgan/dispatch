import type { VercelRequest, VercelResponse } from "@vercel/node";

const BACKEND_URL = process.env.PODCAST_BACKEND_URL || process.env.VITE_DISPATCH_API_URL;

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "GET") return res.status(405).end();

  if (!BACKEND_URL) {
    return res.status(503).json({ error: "Backend URL not configured" });
  }

  try {
    const response = await fetch(`${BACKEND_URL}/api/admin/system/setup-status`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    const data = await response.json();
    res.status(response.status).json(data);
  } catch (e) {
    res.status(502).json({ error: String(e) });
  }
}
