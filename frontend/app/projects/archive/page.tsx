import { fetchSnapshot } from "@/lib/snapshot";
import Masthead from "@/components/Masthead";
import Link from "next/link";

export const metadata = {
  title: "Archive — Dispatch",
};

export default async function ArchivePage() {
  const snapshot = await fetchSnapshot();
  const archived = snapshot?.projects.filter((p) => p.status === "archived") ?? [];

  return (
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
            {archived.map((p) => (
              <Link
                key={p.slug}
                href={`/projects/${p.slug}`}
                className="flex items-center gap-3 py-3 border-b border-ink/5 group"
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
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
