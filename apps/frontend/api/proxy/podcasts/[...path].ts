import type { VercelRequest, VercelResponse } from "@vercel/node";

const PODCAST_BACKEND = process.env.PODCAST_BACKEND_URL;

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (!PODCAST_BACKEND) {
    return res.status(503).json({ error: "PODCAST_BACKEND_URL not configured" });
  }
  const path = (req.query.path as string[]) || [];
  const target = `${PODCAST_BACKEND}/api/podcasts/${path.join("/")}`;

  try {
    const response = await fetch(target, {
      method: req.method,
      headers: { "Content-Type": "application/json" },
      body: req.method !== "GET" && req.method !== "HEAD" ? JSON.stringify(req.body) : undefined,
    });
    const data = await response.text();
    res.setHeader("Content-Type", response.headers.get("content-type") || "application/json");
    res.status(response.status).send(data);
  } catch (e) {
    res.status(502).json({ error: String(e) });
  }
}
