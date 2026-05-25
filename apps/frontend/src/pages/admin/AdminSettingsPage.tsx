import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listSettings, bulkUpdateSettings } from "@/lib/api";

interface Setting {
  key: string;
  value: string;
}

const CATEGORIES = [
  { prefix: "ai", label: "AI" },
  { prefix: "tts", label: "TTS" },
  { prefix: "github", label: "GitHub" },
  { prefix: "storage", label: "Storage" },
  { prefix: "podcast", label: "Podcast" },
  { prefix: "web", label: "Web / CORS" },
];

// Known keys per category — surface them as empty editable rows when
// they're not yet set, so operators can configure on first visit
// without having to know the key names ahead of time.
const KNOWN_KEYS: Record<string, string[]> = {
  ai: ["ai.provider"],
  tts: ["tts.provider"],
  github: ["github.global_token"],
  storage: [
    "storage.provider",
    "storage.local_root",
    "storage.r2_account_id",
    "storage.r2_bucket",
    "storage.r2_access_key_id",
    "storage.r2_secret_access_key",
    "storage.r2_public_base_url",
    "storage.s3_endpoint",
    "storage.s3_bucket",
    "storage.s3_access_key_id",
    "storage.s3_secret_access_key",
    "storage.s3_region",
    "storage.s3_public_base_url",
  ],
  podcast: [
    "podcast.notebooklm_session",
    "podcast.notebooklm_status",
  ],
  web: ["web.allowed_origins", "snapshot.public"],
};

export default function AdminSettingsPage() {
  const [activeCategory, setActiveCategory] = useState("storage");
  const [settings, setSettings] = useState<Setting[]>([]);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    loadCategory(activeCategory);
  }, [activeCategory]);

  async function loadCategory(prefix: string) {
    setLoading(true);
    setError("");
    setSavedMsg("");
    try {
      const data = await listSettings(prefix);
      const rows: Setting[] = data.settings ?? data ?? [];
      // Merge with KNOWN_KEYS so unset keys still appear as editable
      // empty fields. Stored keys take precedence (preserve their value).
      const byKey = new Map<string, Setting>();
      (KNOWN_KEYS[prefix] ?? []).forEach((k) => byKey.set(k, { key: k, value: "" }));
      rows.forEach((s) => byKey.set(s.key, s));
      const merged = Array.from(byKey.values()).sort((a, b) => a.key.localeCompare(b.key));
      setSettings(merged);
      const map: Record<string, string> = {};
      merged.forEach((s) => {
        map[s.key] = s.value ?? "";
      });
      setDraft(map);
    } catch (e) {
      setError("Failed to load settings.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setError("");
    setSavedMsg("");
    try {
      await bulkUpdateSettings(draft);
      setSavedMsg("Saved.");
      await loadCategory(activeCategory);
    } catch (e: any) {
      setError(e.message || "Failed to save settings.");
    } finally {
      setSaving(false);
    }
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
            className="text-[11px] uppercase tracking-[var(--tracking-nav)] px-3 py-2.5 font-medium text-ink-mute hover:text-ink transition-colors"
          >
            Projects
          </Link>
          <Link
            to="/admin/settings"
            className="text-[11px] uppercase tracking-[var(--tracking-nav)] px-3 py-2.5 font-medium text-ink border-b-2 border-ink"
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

      {/* Category tabs */}
      <div className="flex gap-0 border border-ink mb-8">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.prefix}
            onClick={() => setActiveCategory(cat.prefix)}
            className={`flex-1 font-mono text-[11px] uppercase tracking-[0.14em] font-semibold px-4 py-3 border-r border-ink last:border-r-0 transition-colors ${
              activeCategory === cat.prefix
                ? "bg-ink text-paper"
                : "bg-paper text-ink hover:bg-paper-deep"
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-6 px-4 py-3 border border-signal text-signal font-mono text-[11px]">
          {error}
        </div>
      )}
      {savedMsg && (
        <div className="mb-6 px-4 py-3 border border-ink text-ink font-mono text-[11px]">
          {savedMsg}
        </div>
      )}

      {loading ? (
        <p className="font-disp text-sm text-ink-mute py-4">Loading…</p>
      ) : settings.length === 0 ? (
        <p className="font-disp text-sm text-ink-mute py-4">
          No settings found for this category.
        </p>
      ) : (
        <div className="border border-ink mb-8">
          {settings.map((s) => (
            <div
              key={s.key}
              className="grid grid-cols-1 sm:grid-cols-[1fr_2fr] gap-0 border-b border-hair last:border-b-0 items-center px-4 py-3 hover:bg-paper-deep transition-colors"
            >
              <label className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-mute font-semibold truncate pr-4">
                {s.key}
              </label>
              <input
                type="text"
                className="w-full px-2.5 py-2 border border-ink bg-paper font-disp text-sm text-ink focus:outline-none focus:border-signal"
                value={draft[s.key] ?? ""}
                onChange={(e) =>
                  setDraft({ ...draft, [s.key]: e.target.value })
                }
              />
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center gap-4">
        <button
          onClick={handleSave}
          disabled={saving || loading}
          className="font-mono text-[11px] uppercase tracking-[0.14em] font-semibold px-6 py-2.5 bg-signal text-paper hover:bg-ink transition-colors disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
    </main>
  );
}
