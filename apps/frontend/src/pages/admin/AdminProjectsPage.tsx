import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  listAdminProjects,
  createAdminProject,
  updateAdminProject,
  deleteAdminProject,
} from "@/lib/api";
import { suggestDisplayName } from "@/lib/projectNames";

interface Project {
  slug: string;
  display_name: string;
  github_repo: string;
  status: string;
  kind: string;
}

export default function AdminProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [editingSlug, setEditingSlug] = useState<string | null>(null);
  const [error, setError] = useState("");

  const [form, setForm] = useState({
    slug: "",
    display_name: "",
    github_repo: "",
    status: "active",
    kind: "app",
  });

  const [editForm, setEditForm] = useState<Project | null>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  async function loadProjects() {
    setLoading(true);
    setError("");
    try {
      const data = await listAdminProjects();
      setProjects(data.projects ?? data ?? []);
    } catch (e: any) {
      console.error("Failed to load projects:", e);
      setError(e.message || "Failed to load projects.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError("");
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
      await loadProjects();
    } catch (e: any) {
      setError(e.message || "Failed to create project.");
    }
  }

  async function handleSaveEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!editForm) return;
    setError("");
    try {
      await updateAdminProject(editForm.slug, editForm);
      setEditingSlug(null);
      setEditForm(null);
      await loadProjects();
    } catch (e: any) {
      setError(e.message || "Failed to update project.");
    }
  }

  async function handleDelete(slug: string) {
    if (!confirm(`Delete project "${slug}"?`)) return;
    setError("");
    try {
      await deleteAdminProject(slug);
      await loadProjects();
    } catch (e: any) {
      setError(e.message || "Failed to delete project.");
    }
  }

  function startEdit(p: Project) {
    setEditingSlug(p.slug);
    setEditForm({ ...p });
    setCreating(false);
  }

  function cancelEdit() {
    setEditingSlug(null);
    setEditForm(null);
  }

  if (loading) {
    return (
      <main className="max-w-[1400px] mx-auto px-4 sm:px-8 py-24 text-center">
        <p className="font-disp text-base text-ink-soft">Loading…</p>
      </main>
    );
  }

  return (
    <main className="max-w-[1400px] mx-auto px-4 sm:px-8 py-12">
      <header className="mb-10">
        <h1 className="font-disp text-2xl font-bold tracking-[-0.02em] text-ink">
          Admin
        </h1>
        <div className="mt-3 flex gap-0 font-mono overflow-x-auto border-b border-ink">
          <Link
            to="/admin"
            className="text-[11px] uppercase tracking-[var(--tracking-nav)] px-3 py-2.5 font-medium text-ink-mute hover:text-ink transition-colors"
          >
            Dashboard
          </Link>
          <Link
            to="/admin/projects"
            className="text-[11px] uppercase tracking-[var(--tracking-nav)] px-3 py-2.5 font-medium text-ink border-b-2 border-ink"
          >
            Projects
          </Link>
          <Link
            to="/admin/settings"
            className="text-[11px] uppercase tracking-[var(--tracking-nav)] px-3 py-2.5 font-medium text-ink-mute hover:text-ink transition-colors"
          >
            Settings
          </Link>
          <Link
            to="/admin/runs"
            className="text-[11px] uppercase tracking-[var(--tracking-nav)] px-3 py-2.5 font-medium text-ink-mute hover:text-ink transition-colors"
          >
            Runs
          </Link>
        </div>
      </header>

      {error && (
        <div className="mb-6 px-4 py-3 border border-signal text-signal font-mono text-[11px]">
          {error}
        </div>
      )}

      {/* Create */}
      {!creating ? (
        <div className="mb-8">
          <button
            onClick={() => {
              setCreating(true);
              setEditingSlug(null);
            }}
            className="font-mono text-[11px] uppercase tracking-[0.14em] font-semibold px-5 py-2.5 bg-signal text-paper hover:bg-ink transition-colors"
          >
            + New Project
          </button>
        </div>
      ) : (
        <form
          onSubmit={handleCreate}
          className="mb-10 border border-ink p-5 bg-paper-deep"
        >
          <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink font-semibold mb-4">
            New Project
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-4">
            <Field
              label="Slug"
              value={form.slug}
              onChange={(v) => setForm({ ...form, slug: v })}
              required
            />
            <Field
              label="Display Name"
              value={form.display_name}
              onChange={(v) => setForm({ ...form, display_name: v })}
              required
            />
            <Field
              label="GitHub Repo"
              value={form.github_repo}
              onChange={(v) => {
                const suggested = suggestDisplayName(v);
                setForm((prev) => ({
                  ...prev,
                  github_repo: v,
                  display_name: prev.display_name || suggested || prev.display_name,
                }));
              }}
              placeholder="owner/repo"
            />
            <SelectField
              label="Status"
              value={form.status}
              onChange={(v) => setForm({ ...form, status: v })}
              options={["active", "held", "archived"]}
            />
            <SelectField
              label="Kind"
              value={form.kind}
              onChange={(v) => setForm({ ...form, kind: v })}
              options={["app", "lib", "infra", "other"]}
            />
          </div>
          <div className="flex gap-3">
            <button
              type="submit"
              className="font-mono text-[11px] uppercase tracking-[0.14em] font-semibold px-5 py-2.5 bg-signal text-paper hover:bg-ink transition-colors"
            >
              Create
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
              }}
              className="font-mono text-[11px] uppercase tracking-[0.14em] font-semibold px-5 py-2.5 border border-ink text-ink hover:bg-paper-deep transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* List */}
      <div className="border border-ink">
        <div className="grid grid-cols-[1fr_1fr_120px_80px_100px] sm:grid-cols-[1fr_1fr_140px_100px_120px] gap-0 bg-paper-deep border-b border-ink">
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-mute px-3 py-2 font-semibold">
            Slug
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-mute px-3 py-2 font-semibold">
            Name
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-mute px-3 py-2 font-semibold">
            Repo
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-mute px-3 py-2 font-semibold">
            Status
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-mute px-3 py-2 font-semibold text-right">
            Actions
          </span>
        </div>

        {projects.length === 0 && (
          <div className="px-3 py-6 text-center font-disp text-sm text-ink-mute">
            No projects yet.
          </div>
        )}

        {projects.map((p) =>
          editingSlug === p.slug && editForm ? (
            <form
              key={p.slug}
              onSubmit={handleSaveEdit}
              className="grid grid-cols-[1fr_1fr_120px_80px_100px] sm:grid-cols-[1fr_1fr_140px_100px_120px] gap-0 border-b border-hair bg-paper-deep items-center"
            >
              <span className="font-mono text-[11px] text-ink-mute px-3 py-2.5 truncate">
                {p.slug}
              </span>
              <input
                className="w-full px-3 py-2 border border-ink bg-paper font-disp text-sm text-ink focus:outline-none focus:border-signal"
                value={editForm.display_name}
                onChange={(e) =>
                  setEditForm({ ...editForm, display_name: e.target.value })
                }
                required
              />
              <input
                className="w-full px-3 py-2 border border-ink bg-paper font-disp text-sm text-ink focus:outline-none focus:border-signal"
                value={editForm.github_repo}
                onChange={(e) =>
                  setEditForm({ ...editForm, github_repo: e.target.value })
                }
              />
              <select
                className="w-full px-3 py-2 border border-ink bg-paper font-mono text-[11px] text-ink focus:outline-none focus:border-signal"
                value={editForm.status}
                onChange={(e) =>
                  setEditForm({ ...editForm, status: e.target.value })
                }
              >
                <option value="active">active</option>
                <option value="held">held</option>
                <option value="archived">archived</option>
              </select>
              <div className="flex gap-2 justify-end px-3 py-2">
                <button
                  type="submit"
                  className="font-mono text-[10px] uppercase tracking-[0.12em] font-semibold px-2.5 py-1 bg-signal text-paper hover:bg-ink transition-colors"
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={cancelEdit}
                  className="font-mono text-[10px] uppercase tracking-[0.12em] font-semibold px-2.5 py-1 border border-ink text-ink hover:bg-paper-deep transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <div
              key={p.slug}
              className="grid grid-cols-[1fr_1fr_120px_80px_100px] sm:grid-cols-[1fr_1fr_140px_100px_120px] gap-0 border-b border-hair last:border-b-0 items-center hover:bg-paper-deep transition-colors"
            >
              <span className="font-mono text-[11px] text-ink px-3 py-2.5 truncate">
                {p.slug}
              </span>
              <span className="font-disp text-sm font-semibold text-ink px-3 py-2.5 truncate">
                {p.display_name}
              </span>
              <span className="font-mono text-[10px] text-ink-mute px-3 py-2.5 truncate">
                {p.github_repo || "—"}
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-mute px-3 py-2.5">
                {p.status}
              </span>
              <div className="flex gap-2 justify-end px-3 py-2">
                <button
                  onClick={() => startEdit(p)}
                  className="font-mono text-[10px] uppercase tracking-[0.12em] font-semibold px-2.5 py-1 border border-ink text-ink hover:bg-paper-deep transition-colors"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(p.slug)}
                  className="font-mono text-[10px] uppercase tracking-[0.12em] font-semibold px-2.5 py-1 border border-signal text-signal hover:bg-signal hover:text-paper transition-colors"
                >
                  Del
                </button>
              </div>
            </div>
          )
        )}
      </div>
    </main>
  );
}

function Field({
  label,
  value,
  onChange,
  required,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="block font-mono text-[10px] uppercase tracking-[0.22em] text-ink-mute font-semibold mb-1">
        {label}
      </label>
      <input
        className="w-full px-2.5 py-2 border border-ink bg-paper font-disp text-sm text-ink focus:outline-none focus:border-signal placeholder:text-ink-mute/40"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
      />
    </div>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <div>
      <label className="block font-mono text-[10px] uppercase tracking-[0.22em] text-ink-mute font-semibold mb-1">
        {label}
      </label>
      <select
        className="w-full px-2.5 py-2 border border-ink bg-paper font-mono text-[11px] text-ink focus:outline-none focus:border-signal"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  );
}
