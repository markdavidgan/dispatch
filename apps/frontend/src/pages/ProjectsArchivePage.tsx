import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchSnapshot, fetchProjects } from "@/lib/api";
import Seo from "@/components/Seo";
import Masthead from "@/components/Masthead";

export default function ProjectsArchivePage() {
  const [snapshot, setSnapshot] = useState<any>(null);
  const [registry, setRegistry] = useState<any[]>([]);
  useEffect(() => {
    fetchSnapshot().then((data) => setSnapshot(data));
    fetchProjects().then((data) => setRegistry(data ?? []));
  }, []);

  const archived = snapshot?.projects?.filter((p: any) => p.status === "archived") ?? [];

  return (
    <>
      <Seo
        title="Archive"
        description="Archived projects previously tracked by Dispatch."
        canonicalPath="/projects/archive"
      />
      <div className="min-h-screen bg-paper">
        <Masthead />
      <main className="max-w-[1080px] mx-auto px-5 pb-20 py-12">
        <h1 className="font-serif text-headline text-ink mb-4" style={{ fontSize: "var(--text-headline)" }}>
          Archive
        </h1>
        {archived.length === 0 ? (
          <p className="font-sans text-body text-ink-soft" style={{ fontSize: "var(--text-body)" }}>
            No archived projects.
          </p>
        ) : (
          <div className="space-y-0">
            {archived.map((p: any) => {
              const reg = registry.find((r: any) => r.slug === p.slug);
              return (
                <div key={p.slug} className="py-3 border-b border-ink/5">
                  <Link
                    to={`/projects/${p.slug}`}
                    className="flex items-center gap-3 group"
                  >
                    <span className="font-sans text-body text-ink flex-1" style={{ fontSize: "var(--text-body)" }}>
                      {p.name}
                    </span>
                    <span className="font-mono text-label text-ink-soft uppercase" style={{ fontSize: "var(--text-label)" }}>
                      {p.kind}
                    </span>
                    <span className="text-ink-soft opacity-0 group-hover:opacity-100 transition-opacity text-label">
                      →
                    </span>
                  </Link>
                  {reg?.github_repo && (
                    <a
                      href={`https://github.com/${reg.github_repo}`}
                      target="_blank"
                      rel="noreferrer"
                      className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-mute hover:text-ink transition-colors mt-1 block"
                    >
                      {reg.github_repo} ↗
                    </a>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </main>
      </div>
    </>
  );
}
