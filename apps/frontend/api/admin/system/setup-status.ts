import type { VercelRequest, VercelResponse } from "@vercel/node";
import { getDb, ensureSchema } from "../../../_lib/db.js";
import { getSetting } from "../../../_lib/settings.js";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "GET") return res.status(405).end();
  const db = getDb();
  await ensureSchema(db);
  const projectCount = await db.execute({ sql: "SELECT COUNT(*) FROM projects WHERE kind != 'meta'", args: [] });

  const storage_provider = await getSetting("storage.provider");
  const ai_provider = await getSetting("ai.provider");
  const tts_provider = await getSetting("tts.provider");
  const github_token = await getSetting("github.global_token");

  res.status(200).json({
    storage_provider: storage_provider || "local",
    ai_provider: ai_provider || null,
    tts_provider: tts_provider || null,
    github_token_present: Boolean(github_token || process.env.GITHUB_TOKEN),
    project_count: Number(projectCount.rows[0]?.[0] || 0),
  });
}
