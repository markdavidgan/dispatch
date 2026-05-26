import { createClient } from "@libsql/client";
import { readFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const url = process.env.TURSO_DATABASE_URL;
const authToken = process.env.TURSO_AUTH_TOKEN;
if (!url || !authToken) {
  console.error("TURSO_DATABASE_URL and TURSO_AUTH_TOKEN required");
  process.exit(1);
}

const client = createClient({ url, authToken });

async function seed() {
  const schema = readFileSync(join(__dirname, "schema.sql"), "utf-8");
  await client.executeMultiple(schema);

  const defaults = [
    { job_name: "synthesis_lead", cron: "0 1 * * *", timezone: "Asia/Manila", is_enabled: 1 },
    { job_name: "housekeeping", cron: "0 2 * * *", timezone: "UTC", is_enabled: 1 },
    { job_name: "from_the_desk", cron: "0 23 * * 0", timezone: "Asia/Manila", is_enabled: 1 },
  ];

  for (const s of defaults) {
    await client.execute({
      sql: `INSERT OR IGNORE INTO schedules (job_name, cron_expression, timezone, is_enabled) VALUES (?, ?, ?, ?)`,
      args: [s.job_name, s.cron, s.timezone, s.is_enabled],
    });
  }

  console.log("Seeded Turso database");
}

seed().catch((e) => { console.error(e); process.exit(1); });
