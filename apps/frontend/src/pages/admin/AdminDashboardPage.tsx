import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchSetupStatus, triggerBackup, listRuns } from "@/lib/api";
import { formatDateTimeLocal } from "@/lib/time";

interface SetupStatus {
  storage_provider?: string;
  ai_provider?: string;
  tts_provider?: string;
  github_token_present?: boolean;
  project_count?: number;
}

interface Run {
  id: number;
  job_name: string;
  status: string;
  started_at: string;
  events_added?: number;
  error?: string;
}

export default function AdminDashboardPage() {
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [backingUp, setBackingUp] = useState(false);
  const [backupMsg, setBackupMsg] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const [s, r] = await Promise.all([
          fetchSetupStatus(),
          listRuns("?limit=10&offset=0"),
        ]);
        setStatus(s);
        setRuns(r.runs ?? r ?? []);
      } catch (e: any) {
        console.error(e);
        setError(e.message || "Failed to load dashboard data.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleBackup() {
    setBackingUp(true);
    setBackupMsg("");
    try {
      await triggerBackup();
      setBackupMsg("Backup triggered.");
      const r = await listRuns("?limit=10&offset=0");
      setRuns(r.runs ?? r ?? []);
    } catch (e) {
      setBackupMsg("Backup failed.");
    } finally {
      setBackingUp(false);
    }
  }

  if (loading) {
    return (
      <main className="max-w-[1400px] mx-auto px-4 sm:px-8 py-24 text-center">
        <p className="font-disp text-base text-ink-soft">Loading…</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="max-w-[1400px] mx-auto px-4 sm:px-8 py-12">
        <header className="mb-10">
          <h1 className="font-disp text-2xl font-bold tracking-[-0.02em] text-ink">Admin</h1>
        </header>
        <div className="border border-signal p-5">
          <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-signal font-semibold">Error</p>
          <p className="font-disp text-sm text-ink mt-2">{error}</p>
        </div>
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
            className="text-[11px] uppercase tracking-[var(--tracking-nav)] px-3 py-2.5 font-medium text-ink border-b-2 border-ink"
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

      {/* Status Cards */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-0 border border-ink mb-12">
        <StatusCard label="Storage" value={status?.storage_provider ?? "—"} />
        <StatusCard label="AI" value={status?.ai_provider ?? "—"} />
        <StatusCard label="TTS" value={status?.tts_provider ?? "—"} />
        <StatusCard
          label="GitHub Token"
          value={status?.github_token_present ? "Configured" : "Missing"}
          signal={!status?.github_token_present}
        />
        <StatusCard
          label="Projects"
          value={String(status?.project_count ?? 0)}
        />
      </section>

      {/* Actions */}
      <section className="mb-12">
        <div className="flex items-center gap-4">
          <button
            onClick={handleBackup}
            disabled={backingUp}
            className="font-mono text-[11px] uppercase tracking-[0.14em] font-semibold px-5 py-2.5 bg-signal text-paper hover:bg-ink transition-colors disabled:opacity-50"
          >
            {backingUp ? "Triggering…" : "Trigger Backup"}
          </button>
          {backupMsg && (
            <span className="font-mono text-[11px] text-ink-mute">
              {backupMsg}
            </span>
          )}
        </div>
      </section>

      {/* Latest Runs */}
      <section>
        <div className="flex items-baseline justify-between pb-3 border-b border-ink mb-4">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink font-semibold">
            Latest Runs
          </h2>
          <Link
            to="/admin/runs"
            className="font-mono text-[11px] uppercase tracking-[0.14em] text-ink-mute hover:text-ink transition-colors"
          >
            View all →
          </Link>
        </div>

        {runs.length === 0 ? (
          <p className="font-disp text-sm text-ink-mute py-4">No runs yet.</p>
        ) : (
          <div className="border border-ink">
            <div className="grid grid-cols-[1fr_100px_140px_80px] gap-0 bg-paper-deep border-b border-ink">
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-mute px-3 py-2 font-semibold">
                Job
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-mute px-3 py-2 font-semibold">
                Status
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-mute px-3 py-2 font-semibold">
                Started
              </span>
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-mute px-3 py-2 font-semibold text-right">
                Events
              </span>
            </div>
            {runs.map((run) => (
              <div
                key={run.id}
                className="grid grid-cols-[1fr_100px_140px_80px] gap-0 border-b border-hair last:border-b-0 items-center hover:bg-paper-deep transition-colors"
              >
                <span className="font-disp text-sm font-semibold text-ink px-3 py-2.5 truncate">
                  {run.job_name}
                </span>
                <span
                  className={`font-mono text-[10px] uppercase tracking-[0.14em] px-3 py-2.5 font-semibold ${
                    run.status === "completed"
                      ? "text-ink"
                      : run.status === "failed"
                        ? "text-signal"
                        : "text-ink-mute"
                  }`}
                >
                  {run.status}
                </span>
                <span className="font-mono text-[11px] text-ink-mute px-3 py-2.5">
                  {formatDateTimeLocal(run.started_at)}
                </span>
                <span className="font-mono text-[11px] text-ink px-3 py-2.5 text-right tabular-nums">
                  {run.events_added ?? "—"}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

function StatusCard({
  label,
  value,
  signal,
}: {
  label: string;
  value: string;
  signal?: boolean;
}) {
  return (
    <div className="px-4 py-4 border-r border-ink last:border-r-0">
      <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-ink-mute font-semibold mb-1.5">
        {label}
      </div>
      <div
        className={`font-disp text-lg font-bold tracking-[-0.01em] truncate ${
          signal ? "text-signal" : "text-ink"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
