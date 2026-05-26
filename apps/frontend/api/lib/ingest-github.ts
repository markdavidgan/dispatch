import { getDb } from "./db";

interface GitHubEvent {
  project_slug: string;
  kind: string;
  external_id: string;
  title: string;
  body?: string;
  url?: string;
  author?: string;
  occurred_at: string;
  ingested_at: string;
}

async function getGitHubToken(): Promise<string | undefined> {
  const { getSetting } = await import("./settings");
  return getSetting("github.token") || process.env.GITHUB_TOKEN || undefined;
}

async function fetchPage(url: string, token?: string): Promise<any[]> {
  const headers: Record<string, string> = {
    Accept: "application/vnd.github.v3+json",
    "User-Agent": "dispatch-collector",
  };
  if (token) headers.Authorization = `token ${token}`;

  const resp = await fetch(url, { headers });
  if (!resp.ok) {
    throw new Error(`GitHub API error: ${resp.status} ${resp.statusText}`);
  }
  return resp.json() as Promise<any[]>;
}

export async function ingestRepo(projectSlug: string, repo: string): Promise<number> {
  const db = getDb();
  const token = await getGitHubToken();
  const [owner, name] = repo.split("/");
  if (!owner || !name) throw new Error(`Invalid repo: ${repo}`);

  // Get cursor
  const cursorRow = await db.execute({
    sql: "SELECT cursor FROM cursors WHERE project_slug = ? AND source = ?",
    args: [projectSlug, `github:${repo}`],
  });
  const since = cursorRow.rows[0]?.cursor as string | undefined;

  let page = 1;
  let totalInserted = 0;
  let latestCursor: string | undefined;

  // PRs (opened + merged)
  const prsUrl = `https://api.github.com/repos/${owner}/${name}/pulls?state=all&sort=updated&direction=desc&per_page=100${since ? `&since=${since}` : ""}`;
  const prs = await fetchPage(prsUrl, token);

  for (const pr of prs) {
    const updatedAt = pr.updated_at;
    if (since && updatedAt <= since) continue;
    if (!latestCursor || updatedAt > latestCursor) latestCursor = updatedAt;

    const kind = pr.merged_at ? "pr_merged" : "pr_opened";
    const occurredAt = pr.merged_at || pr.created_at;

    try {
      await db.execute({
        sql: `INSERT OR IGNORE INTO events (project_slug, kind, external_id, title, body, url, author, occurred_at, ingested_at, meta)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        args: [
          projectSlug,
          kind,
          String(pr.number),
          pr.title,
          pr.body || "",
          pr.html_url,
          pr.user?.login || "",
          occurredAt,
          new Date().toISOString(),
          JSON.stringify({ state: pr.state }),
        ],
      });
      totalInserted++;
    } catch (e) {
      // ignore duplicates
    }
  }

  // Issues
  const issuesUrl = `https://api.github.com/repos/${owner}/${name}/issues?state=all&sort=updated&direction=desc&per_page=100${since ? `&since=${since}` : ""}`;
  const issues = await fetchPage(issuesUrl, token);

  for (const issue of issues) {
    if ("pull_request" in issue) continue; // skip PRs returned as issues
    const updatedAt = issue.updated_at;
    if (since && updatedAt <= since) continue;
    if (!latestCursor || updatedAt > latestCursor) latestCursor = updatedAt;

    try {
      await db.execute({
        sql: `INSERT OR IGNORE INTO events (project_slug, kind, external_id, title, body, url, author, occurred_at, ingested_at, meta)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        args: [
          projectSlug,
          "issue",
          String(issue.number),
          issue.title,
          issue.body || "",
          issue.html_url,
          issue.user?.login || "",
          issue.created_at,
          new Date().toISOString(),
          JSON.stringify({ state: issue.state }),
        ],
      });
      totalInserted++;
    } catch (e) {
      // ignore duplicates
    }
  }

  // Releases
  const releasesUrl = `https://api.github.com/repos/${owner}/${name}/releases?per_page=30`;
  const releases = await fetchPage(releasesUrl, token);

  for (const release of releases) {
    const publishedAt = release.published_at;
    if (since && publishedAt <= since) continue;
    if (!latestCursor || publishedAt > latestCursor) latestCursor = publishedAt;

    try {
      await db.execute({
        sql: `INSERT OR IGNORE INTO events (project_slug, kind, external_id, title, body, url, author, occurred_at, ingested_at, meta)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        args: [
          projectSlug,
          "release",
          release.tag_name,
          release.name || release.tag_name,
          release.body || "",
          release.html_url,
          release.author?.login || "",
          publishedAt,
          new Date().toISOString(),
          JSON.stringify({}),
        ],
      });
      totalInserted++;
    } catch (e) {
      // ignore duplicates
    }
  }

  // Update cursor
  if (latestCursor) {
    await db.execute({
      sql: `INSERT INTO cursors (project_slug, source, cursor, updated_at) VALUES (?, ?, ?, ?)
            ON CONFLICT(project_slug, source) DO UPDATE SET cursor = excluded.cursor, updated_at = excluded.updated_at`,
      args: [projectSlug, `github:${repo}`, latestCursor, new Date().toISOString()],
    });
  }

  return totalInserted;
}
