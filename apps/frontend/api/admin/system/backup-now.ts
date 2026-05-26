import type { VercelRequest, VercelResponse } from "@vercel/node";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "POST") return res.status(405).end();
  // Backup is a no-op on Turso (managed), but we can trigger a dump if needed.
  res.status(200).json({ ok: true, note: "Turso backups are automatic" });
}
