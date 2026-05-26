import { getDb } from "./db.js";
import { encrypt, decrypt } from "./crypto.js";

export async function getSetting(key: string): Promise<string | null> {
  const db = getDb();
  const row = await db.execute({
    sql: "SELECT value FROM settings WHERE key = ?",
    args: [key],
  });
  if (!row.rows.length) return null;
  const encrypted = row.rows[0].value as string;
  return decrypt(encrypted);
}

export async function setSetting(key: string, value: string): Promise<void> {
  const db = getDb();
  const encrypted = await encrypt(value);
  const updatedAt = new Date().toISOString();
  await db.execute({
    sql: `INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)
          ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at`,
    args: [key, encrypted, updatedAt],
  });
}

export async function listSettings(prefix = ""): Promise<Record<string, string>> {
  const db = getDb();
  const rows = await db.execute({
    sql: "SELECT key, value FROM settings WHERE key LIKE ? ORDER BY key",
    args: [`${prefix}%`],
  });
  const out: Record<string, string> = {};
  for (const r of rows.rows) {
    out[r.key as string] = await decrypt(r.value as string);
  }
  return out;
}
