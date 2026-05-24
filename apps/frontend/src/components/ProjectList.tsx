import { Link } from "react-router-dom";

interface ProjectLine {
  slug: string;
  name: string;
  status: string;
  kind?: string;
  stat: string;
  bullet: "red" | "amber" | "sand";
}

interface LiveStats {
  open_prs: number;
  commits_7d: number;
  last_commit_at: string | null;
}

interface Props {
  projects: ProjectLine[];
  liveStats?: Record<string, LiveStats>;
}

function Bullet({ color }: { color: ProjectLine["bullet"] }) {
  const base = "inline-block w-2 h-2 rounded-full";
  if (color === "red")
    return (
      <span
        className={`${base} bg-signal`}
        style={{ animation: "bullet-pulse 2.4s ease-in-out infinite" }}
      />
    );
  if (color === "amber") return <span className={`${base} bg-ink`} />;
  return <span className={`${base} border border-ink-mute opacity-50`} />;
}

export default function ProjectList({ projects, liveStats }: Props) {
  const active = projects.filter((p) => p.status === "active");
  const held = projects.filter((p) => p.status === "held");

  return (
    <section className="mt-16 pt-5 border-t border-ink">
      <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink pb-3.5 font-semibold flex justify-between items-baseline">
        Projects
        <span className="text-ink-mute font-normal">
          {String(active.length).padStart(2, "0")} active · {String(held.length).padStart(2, "0")} held
        </span>
      </h2>
      <div>
        {active.map((p) => (
          <ProjectRow key={p.slug} project={p} live={liveStats?.[p.slug]} />
        ))}
        {held.length > 0 && (
          <div className="my-4 relative h-px bg-ink">
            <span className="absolute left-1/2 -translate-x-1/2 -top-[7px] bg-paper px-3.5 font-mono text-[10px] uppercase tracking-[0.24em] text-ink font-semibold">
              HELD
            </span>
          </div>
        )}
        {held.map((p) => (
          <ProjectRow key={p.slug} project={p} live={liveStats?.[p.slug]} dimmed />
        ))}
      </div>
    </section>
  );
}

function ProjectRow({
  project,
  live,
  dimmed,
}: {
  project: ProjectLine;
  live?: LiveStats;
  dimmed?: boolean;
}) {
  return (
    <Link
      to={`/projects/${project.slug}`}
      className={`grid grid-cols-[18px_1fr_90px_100px_24px] gap-4 items-center py-3 border-b border-hair hover:bg-paper-deep transition-colors duration-[120ms] ${dimmed ? "opacity-55" : ""}`}
    >
      <Bullet color={project.bullet} />
      <span className="font-disp text-[17px] font-semibold tracking-[-0.01em] text-ink">
        {project.name}
      </span>
      <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-mute">
        {project.kind ?? ""}
      </span>
      <span className="font-mono text-xs text-ink text-right tabular-nums">
        {live ? `${live.commits_7d}c · ${live.open_prs}p` : project.stat}
      </span>
      <span className="font-mono text-sm text-ink-mute text-right">→</span>
    </Link>
  );
}
