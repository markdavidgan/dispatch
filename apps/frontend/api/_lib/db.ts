import { createClient, Client } from "@libsql/client";
import { readFileSync } from "fs";
import { fileURLToPath } from "url";

let _client: Client | null = null;
let _schemaPromise: Promise<void> | null = null;

export function getDb(): Client {
  if (!_client) {
    const url = process.env.TURSO_DATABASE_URL;
    const authToken = process.env.TURSO_AUTH_TOKEN;
    if (!url || !authToken) {
      // Fallback to local SQLite for development
      console.warn("TURSO_DATABASE_URL and TURSO_AUTH_TOKEN not set; using local SQLite fallback");
      _client = createClient({ url: "file:/tmp/dispatch-local.db" });
    } else {
      _client = createClient({ url, authToken });
    }
  }
  return _client;
}

function parseSchemaStatements(sql: string): string[] {
  const statements: string[] = [];
  let current = "";
  for (const line of sql.split("\n")) {
    const trimmed = line.trim();
    if (trimmed.startsWith("--") || trimmed === "") continue;
    current += trimmed + "\n";
    if (trimmed.endsWith(";")) {
      statements.push(current.trim());
      current = "";
    }
  }
  if (current.trim()) {
    statements.push(current.trim());
  }
  return statements;
}

async function _doEnsureSchema(db: Client): Promise<void> {
  try {
    // Fast path: check if projects table already exists
    const check = await db.execute(
      "SELECT name FROM sqlite_master WHERE type='table' AND name='projects'"
    );
    if (check.rows.length > 0) return;

    // Read and apply schema
    const schemaPath = fileURLToPath(new URL("../../turso/schema.sql", import.meta.url));
    const sql = readFileSync(schemaPath, "utf-8");
    const statements = parseSchemaStatements(sql);
    if (statements.length > 0) {
      await db.migrate(statements);
    }
  } catch (e) {
    console.warn("Schema initialization warning:", e);
  }
}

export async function ensureSchema(db?: Client): Promise<void> {
  const client = db ?? getDb();
  if (!_schemaPromise) {
    _schemaPromise = _doEnsureSchema(client);
  }
  return _schemaPromise;
}
