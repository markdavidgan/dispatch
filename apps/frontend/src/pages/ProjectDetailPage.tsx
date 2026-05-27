import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { fetchSnapshot, fetchProjects, updateAdminProject, deleteAdminProject } from "@/lib/api";
import { suggestDisplayName } from "@/lib/projectNames";
import Seo from "@/components/Seo";
import FromTheDesk from "@/components/FromTheDesk";
import MentionedInBriefings from "@/components/MentionedInBriefings";
import EventStream from "@/components/EventStream";

export default function ProjectDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const [snapshot, setSnapshot] = useState<any>(null);
  const [registry, setRegistry] = useState<any[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [editForm, setEditForm] = useState<{
    display_name: string;
    github_repo: string;
    status: string;
    kind: string;
  } | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [snap, reg] = await Promise.all([fetchSnapshot(), fetchProjects()]);
      setSnapshot(snap);
      setRegistry(reg);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [slug]);

  function startEdit(project: any) {
    setEditForm({
      display_name: project.name ?? project.display_name ?? "",
      github_repo: project.github_repo ?? "",
      status: project.status ?? "active",
      kind: project.kind ?? "app",
    });
    setIsEditing(true);
    setError("");
  }

  function cancelEdit() {
    setIsEditing(false);
    setEditForm(null);
    setError("");
  }

  async function handleSave() {
    if (!editForm || !slug) return;
    setSaving(true);
    setError("");
    try {
      await updateAdminProject(slug, editForm);
      setIsEditing(false);
      setEditForm(null);
      await load();
    } catch (e: any) {
      setError(e.message || "Failed to save project.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!slug) return;
    if (!confirm(`Delete project "${slug}"? This cannot be undone.`)) return;
    setSaving(true);
    setError("");
    try {
      await deleteAdminProject(slug);
      navigate("/projects");
    } catch (e: any) {
      setError(e.message || "Failed to delete project.");
      setSaving(false);
    }
  }

  // Check if project is in the latest briefing (covers the window where
  // briefing_mentions table hasn't been populated yet after a new filing)
  const isInLatestBrief = snapshot?.brief?.projects?.some((p: any) => p.slug === slug) ?? false;

  if (loading) {
    return (
      <>
        <Seo title="Project" canonicalPath={`/projects/${slug}`} />
        <main className="lg:pl-24">
          <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-24 text-center">
            <p className="font-disp text-base text-ink-soft">Loading…</p>
          </div>
        </main>
      </>
    );
  }

  let project: any = snapshot?.projects?.find((p: any) => p.slug === slug);
  const registryProject = registry?.find((p: any) => p.slug === slug);

  if (!project) {
    if (registryProject) {
      project = {
        slug: registryProject.slug,
        name: registryProject.display_name,
        status: registryProject.status,
        kind: registryProject.kind,
        color_hint: registryProject.color_hint,
        from_the_desk: null,
        from_the_desk_generated_at: null,
        mentioned_in_briefings: [],
      };
    }
  }

  if (!project) {
    return (
      <>
        <Seo title="Project not found" canonicalPath={`/projects/${slug}`} />
        <main className="lg:pl-24">
          <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-24 text-center">
            <p className="font-disp text-base text-ink-soft">Project not found.</p>
          </div>
        </main>
      </>
    );
  }

  const events = (snapshot?.recent_events ?? []).filter((e: any) => e.project_slug === slug);
  const mentions = project.mentioned_in_briefings ?? [];

  return (
    <>
      <Seo
        title={project.name}
        description={`${project.name} on Dispatch — tracked project profile and briefing mentions.`}
        canonicalPath={`/projects/${slug}`}
      />
      <main className="lg:pl-24">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-8">
          <section className="pt-10 pb-8 border-b border-ink grid grid-cols-[1fr_auto] gap-8 items-end">
            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-mute mb-3.5">
                <Link to="/projects" className="hover:text-signal">
                  Projects
                </Link>{" "}
                · {project.name}
              </div>
              <div className="flex flex-col sm:flex-row sm:items-baseline gap-2 sm:gap-4.5">
                <h1 className="font-disp text-[42px] sm:text-[84px] font-extrabold leading-[0.95] tracking-[-0.04em] break-words">{project.name}</h1>
                {project.status === "active" && (
                  <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-paper bg-signal px-2.5 py-1.5 font-semibold">
                    Active
                  </span>
                )}
                {project.status === "held" && (
                  <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-paper bg-ink-mute px-2.5 py-1.5 font-semibold">
                    Held
                  </span>
                )}
                {project.status === "archived" && (
                  <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-ink-mute border border-ink-mute px-2.5 py-1.5">
                    Archived
                  </span>
                )}
              </div>
              <div className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-soft mt-4.5 flex gap-6 flex-wrap">
                {project.kind && (
                  <span>
                    <span className="text-ink-mute mr-1">Kind</span>
                    <span className="text-ink font-semibold">{project.kind}</span>
                  </span>
                )}
              </div>
            </div>
            <div className="flex flex-col items-end gap-2.5">
              {registryProject?.github_repo && (
                <a
                  href={`https://github.com/${registryProject.github_repo}`}
                  target="_blank"
                  rel="noreferrer"
                  className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink border border-ink hover:bg-ink hover:text-paper px-3.5 py-2.5 font-medium"
                >
                  GitHub ↗
                </a>
              )}
              {!isEditing && (
                <button
                  onClick={() => startEdit(registryProject ?? project)}
                  className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-mute border border-ink hover:bg-paper-deep px-3.5 py-2.5 font-medium transition-colors"
                >
                  Edit project
                </button>
              )}
            </div>
          </section>

          {isEditing && editForm && (
            <section className="mb-10 border border-ink p-5 bg-paper-deep">
              {error && (
                <div className="mb-4 px-4 py-3 border border-signal text-signal font-mono text-[11px]">
                  {error}
                </div>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
                <div>
                  <label className="block font-mono text-[10px] uppercase tracking-[0.22em] text-ink-mute font-semibold mb-1">
                    Display Name
                  </label>
                  <input
                    className="w-full px-2.5 py-2 border border-ink bg-paper font-disp text-sm text-ink focus:outline-none focus:border-signal"
                    value={editForm.display_name}
                    onChange={(e) => setEditForm({ ...editForm, display_name: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <label className="block font-mono text-[10px] uppercase tracking-[0.22em] text-ink-mute font-semibold mb-1">
                    GitHub Repo
                  </label>
                  <input
                    className="w-full px-2.5 py-2 border border-ink bg-paper font-disp text-sm text-ink focus:outline-none focus:border-signal"
                    value={editForm.github_repo}
                    onChange={(e) => {
                      const suggested = suggestDisplayName(e.target.value);
                      setEditForm({
                        ...editForm,
                        github_repo: e.target.value,
                        display_name: editForm.display_name || suggested || editForm.display_name,
                      });
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
                    value={editForm.status}
                    onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
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
                    value={editForm.kind}
                    onChange={(e) => setEditForm({ ...editForm, kind: e.target.value })}
                  >
                    <option value="app">app</option>
                    <option value="lib">lib</option>
                    <option value="infra">infra</option>
                    <option value="other">other</option>
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-3 flex-wrap">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="font-mono text-[11px] uppercase tracking-[0.14em] font-semibold px-5 py-2.5 bg-signal text-paper hover:bg-ink transition-colors disabled:opacity-50"
                >
                  {saving ? "Saving…" : "Save"}
                </button>
                <button
                  onClick={cancelEdit}
                  disabled={saving}
                  className="font-mono text-[11px] uppercase tracking-[0.14em] font-semibold px-5 py-2.5 border border-ink text-ink hover:bg-paper-deep transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDelete}
                  disabled={saving}
                  className="font-mono text-[11px] uppercase tracking-[0.14em] font-semibold px-5 py-2.5 border border-signal text-signal hover:bg-signal hover:text-paper transition-colors disabled:opacity-50"
                >
                  Delete
                </button>
              </div>
            </section>
          )}

          <div className="pt-12 pb-24 grid grid-cols-1 lg:grid-cols-[minmax(0,8fr)_minmax(0,3fr)] gap-16">
            <article>
              <FromTheDesk body={project.from_the_desk ?? null} generatedAt={project.from_the_desk_generated_at ?? null} />
              <MentionedInBriefings mentions={mentions} isInLatestBrief={isInLatestBrief} />
              <EventStream events={events} limit={20} />
            </article>
            <aside className="font-disp text-sm">
              <section className="mb-10">
                <h3 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink pb-3 border-b border-ink mb-4.5 font-semibold">
                  Project brief
                </h3>
                <p className="text-base leading-[1.55] text-ink-soft italic">{project.summary ?? "—"}</p>
              </section>
            </aside>
          </div>
        </div>
      </main>
    </>
  );
}
