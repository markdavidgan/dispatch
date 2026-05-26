import { createClient, Client } from "@libsql/client";

let _client: Client | null = null;

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
