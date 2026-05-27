import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchProjects, createAdminProject } from "@/lib/api";
import { suggestDisplayName } from "@/lib/projectNames";
import Seo from "@/components/Seo";

export default function ProjectsPage() {
  const [registry, setRegistry] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    slug: "",
    display_name: "",
    github_repo: "",
    status: "active",
    kind: "app",
  });

  async function load() {
    setLoading(true);
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

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await createAdminProject(form);
      setForm({
        slug: "",
        display_name: "",
        github_repo: "",
        status: "active",
        kind: "app",
      });
      setCreating(false);
      await load();
    } catch (e: any) {
      setError(e.message || "Failed to create project.");
    } finally {
      setSaving(false);
    }
  }

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
          <div className="flex items-baseline justify-between gap-4">
            <h1 className="font-disp text-[42px] font-extrabold leading-[1.05] tracking-[-0.025em]">Projects</h1>
            {!creating && (
              <button
                onClick={() => {
                  setCreating(true);
                  setError("");
                }}
                className="font-mono text-[11px] uppercase tracking-[0.14em] font-semibold px-5 py-2.5 bg-signal text-paper hover:bg-ink transition-colors shrink-0"
              >
                + New Project
              </button>
            )}
          </div>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-mute mt-2.5">
            The desk roster · {active.length} active · {held.length} held
          </p>
        </section>

        {error && (
          <div className="mb-6 px-4 py-3 border border-signal text-signal font-mono text-[11px]">
            {error}
          </div>
        )}

        {creating && (
          <form
            onSubmit={handleCreate}
            className="mb-10 border border-ink p-5 bg-paper-deep"
          >
            <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink font-semibold mb-4">
              New Project
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-4">
              <div>
                <label className="block font-mono text-[10px] uppercase tracking-[0.22em] text-ink-mute font-semibold mb-1">
                  Slug
                </label>
                <input
                  className="w-full px-2.5 py-2 border border-ink bg-paper font-disp text-sm text-ink focus:outline-none focus:border-signal"
                  value={form.slug}
                  onChange={(e) => setForm({ ...form, slug: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="block font-mono text-[10px] uppercase tracking-[0.22em] text-ink-mute font-semibold mb-1">
                  Display Name
                </label>
                <input
                  className="w-full px-2.5 py-2 border border-ink bg-paper font-disp text-sm text-ink focus:outline-none focus:border-signal"
                  value={form.display_name}
                  onChange={(e) => setForm({ ...form, display_name: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="block font-mono text-[10px] uppercase tracking-[0.22em] text-ink-mute font-semibold mb-1">
                  GitHub Repo
                </label>
                <input
                  className="w-full px-2.5 py-2 border border-ink bg-paper font-disp text-sm text-ink focus:outline-none focus:border-signal"
                  value={form.github_repo}
                  onChange={(e) => {
                    const suggested = suggestDisplayName(e.target.value);
                    setForm((prev) => ({
                      ...prev,
                      github_repo: e.target.value,
                      display_name: prev.display_name || suggested || prev.display_name,
                    }));
                  }}
                  placeholder="owner/repo"
                />
              </div>
              <div>
                <label className="block font-mono text-[10px] uppercase tracking-[0.22em] text-ink-mute font-semibold mb-1">
                  Status
                </label>
                <select
                  className="w-full px-2.5 py-2 border border-ink bg-paper font-mono text-[11px] text-ink focus:outline-none focus:border-signal"
                  value={form.status}
                  onChange={(e) => setForm({ ...form, status: e.target.value })}
                >
                  <option value="active">active</option>
                  <option value="held">held</option>
                  <option value="archived">archived</option>
                </select>
              </div>
              <div>
                <label className="block font-mono text-[10px] uppercase tracking-[0.22em] text-ink-mute font-semibold mb-1">
                  Kind
                </label>
                <select
                  className="w-full px-2.5 py-2 border border-ink bg-paper font-mono text-[11px] text-ink focus:outline-none focus:border-signal"
                  value={form.kind}
                  onChange={(e) => setForm({ ...form, kind: e.target.value })}
                >
                  <option value="app">app</option>
                  <option value="lib">lib</option>
                  <option value="infra">infra</option>
                  <option value="other">other</option>
                </select>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={saving}
                className="font-mono text-[11px] uppercase tracking-[0.14em] font-semibold px-5 py-2.5 bg-signal text-paper hover:bg-ink transition-colors disabled:opacity-50"
              >
                {saving ? "Creating…" : "Create"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setCreating(false);
                  setForm({
                    slug: "",
                    display_name: "",
                    github_repo: "",
                    status: "active",
                    kind: "app",
                  });
                  setError("");
                }}
                className="font-mono text-[11px] uppercase tracking-[0.14em] font-semibold px-5 py-2.5 border border-ink text-ink hover:bg-paper-deep transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

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
