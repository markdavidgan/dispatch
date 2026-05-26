export type Bullet = "red" | "amber" | "sand";

export function deriveBullet(status: string, events: Iterable<Record<string, any>>): Bullet {
  if (status === "archived") return "sand";

  const kinds = Array.from(events).map((e) => e.kind);
  const commits = kinds.filter((k) => k === "commit").length;
  const merged = kinds.some((k) => k === "pr_merged");
  const released = kinds.some((k) => k === "release");

  if (merged || released) return "red";
  if (status === "active" && commits >= 3) return "red";
  if (commits >= 1) return "amber";
  return "sand";
}

export function deriveActiveCount(projects: Array<Record<string, any>>): string {
  const n = projects.filter((p) => p.bullet === "red").length;
  return `${n}`.padStart(2, "0");
}
