import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchProjects } from "@/lib/api";
import Seo from "@/components/Seo";

export default function ProjectsPage() {
  const [registry, setRegistry] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchProjects();
        setRegistry(data ?? []);
      } catch (e) {
        console.error(e);
        setRegistry([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <>
        <Seo title="Projects" canonicalPath="/projects" />
        <main className="lg:pl-24">
          <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-24 text-center">
            <p className="font-disp text-base text-ink-soft">Loading…</p>
          </div>
        </main>
      </>
    );
  }

  const visible = registry.filter((p) => p.status !== "archived");
  const active = visible.filter((p) => p.status === "active");
  const held = visible.filter((p) => p.status === "held");
  const archivedCount = registry.filter((p) => p.status === "archived").length;

  return (
    <>
      <Seo
        title="Projects"
        description="The desk roster — tracked software projects monitored by Dispatch."
        canonicalPath="/projects"
      />
      <main className="lg:pl-24">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-12">
        <section className="pb-6 border-b border-ink mb-8">
          <h1 className="font-disp text-[42px] font-extrabold leading-[1.05] tracking-[-0.025em]">Projects</h1>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-mute mt-2.5">
            The desk roster · {active.length} active · {held.length} held
          </p>
        </section>

        <ul>
          {active.map((p) => (
            <Row key={p.slug} p={p} />
          ))}
          {held.length > 0 && (
            <li className="my-4 relative h-px bg-ink">
              <span className="absolute left-1/2 -translate-x-1/2 -top-[7px] bg-paper px-3.5 font-mono text-[10px] uppercase tracking-[0.24em] text-ink font-semibold">
                HELD
              </span>
            </li>
          )}
          {held.map((p) => (
            <Row key={p.slug} p={p} dimmed />
          ))}
        </ul>

        {archivedCount > 0 && (
          <div className="mt-12 pt-6 border-t border-hair-strong">
            <Link
              to="/projects/archive"
              className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink hover:text-signal font-medium"
            >
              View archived projects ({archivedCount}) →
            </Link>
          </div>
        )}
      </div>
    </main>
    </>
  );
}

function Row({
  p,
  dimmed,
}: {
  p: { slug: string; display_name: string; kind: string | null; status: string; github_repo?: string | null };
  dimmed?: boolean;
}) {
  return (
    <li>
      <Link
        to={`/projects/${p.slug}`}
        className={`grid grid-cols-[1fr_auto_24px] sm:grid-cols-[1fr_120px_24px] gap-4 items-baseline py-4 border-b border-hair hover:bg-paper-deep ${
          dimmed ? "opacity-55" : ""
        }`}
      >
        <span className="font-disp text-xl font-semibold tracking-[-0.01em]">{p.display_name}</span>
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-mute">{p.kind ?? ""}</span>
        <span className="font-mono text-sm text-ink-mute text-right">→</span>
      </Link>
      {p.github_repo && (
        <div className="pl-0 pb-3 -mt-2">
          <a
            href={`https://github.com/${p.github_repo}`}
            target="_blank"
            rel="noreferrer"
            className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-mute hover:text-ink transition-colors"
            onClick={(e) => e.stopPropagation()}
          >
            {p.github_repo} ↗
          </a>
        </div>
      )}
    </li>
  );
}
