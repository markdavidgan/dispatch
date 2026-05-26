import { getDb } from "./db";

async function getGitHubToken(): Promise<string | undefined> {
  const { getSetting } = await import("./settings");
  return getSetting("github.token") || process.env.GITHUB_TOKEN || undefined;
}

export async function ingestCommits(projectSlug: string, repo: string): Promise<number> {
  const db = getDb();
  const token = await getGitHubToken();
  const [owner, name] = repo.split("/");
  if (!owner || !name) throw new Error(`Invalid repo: ${repo}`);

  // List branches
  const branchesResp = await fetch(`https://api.github.com/repos/${owner}/${name}/branches?per_page=100`, {
    headers: {
      Accept: "application/vnd.github.v3+json",
      "User-Agent": "dispatch-collector",
      ...(token ? { Authorization: `token ${token}` } : {}),
    },
  });
  if (!branchesResp.ok) throw new Error(`GitHub branches error: ${branchesResp.status}`);
  const branches = await branchesResp.json() as Array<{ name: string }>;

  let totalInserted = 0;
  const seenShas = new Set<string>();

  for (const branch of branches) {
    const cursorRow = await db.execute({
      sql: "SELECT cursor FROM cursors WHERE project_slug = ? AND source = ?",
      args: [projectSlug, `github-commits:${repo}:${branch.name}`],
    });
    const since = cursorRow.rows[0]?.cursor as string | undefined;

    const url = `https://api.github.com/repos/${owner}/${name}/commits?sha=${encodeURIComponent(branch.name)}&per_page=100${since ? `&since=${since}` : ""}`;
    const resp = await fetch(url, {
      headers: {
        Accept: "application/vnd.github.v3+json",
        "User-Agent": "dispatch-collector",
        ...(token ? { Authorization: `token ${token}` } : {}),
      },
    });
    if (!resp.ok) continue;

    const commits = await resp.json() as Array<any>;
    let latestCursor: string | undefined;

    for (const commit of commits) {
      const sha = commit.sha as string;
      if (seenShas.has(sha)) continue;
      seenShas.add(sha);

      const occurredAt = commit.commit?.committer?.date || commit.commit?.author?.date;
      if (since && occurredAt <= since) continue;
      if (!latestCursor || occurredAt > latestCursor) latestCursor = occurredAt;

      try {
        await db.execute({
          sql: `INSERT OR IGNORE INTO events (project_slug, kind, external_id, title, body, url, author, occurred_at, ingested_at, meta)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
          args: [
            projectSlug,
            "commit",
            sha,
            commit.commit?.message?.split("\n")[0] || "",
            commit.commit?.message || "",
            commit.html_url,
            commit.commit?.author?.name || commit.author?.login || "",
            occurredAt,
            new Date().toISOString(),
            JSON.stringify({ branch: branch.name }),
          ],
        });
        totalInserted++;
      } catch (e) {
        // ignore duplicates
      }
    }

    if (latestCursor) {
      await db.execute({
        sql: `INSERT INTO cursors (project_slug, source, cursor, updated_at) VALUES (?, ?, ?, ?)
              ON CONFLICT(project_slug, source) DO UPDATE SET cursor = excluded.cursor, updated_at = excluded.updated_at`,
        args: [projectSlug, `github-commits:${repo}:${branch.name}`, latestCursor, new Date().toISOString()],
      });
    }
  }

  return totalInserted;
}
