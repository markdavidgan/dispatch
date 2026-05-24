import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listRuns } from "@/lib/api";
import { formatDateTimeLocal } from "@/lib/time";

interface Run {
  id: number;
  job_name: string;
  status: string;
  started_at: string;
  events_added?: number;
  error?: string;
}

const STATUSES = ["", "completed", "failed", "running", "pending"];

export default function AdminRunsPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [limit] = useState(25);
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [jobFilter, setJobFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    loadRuns();
  }, [offset, jobFilter, statusFilter]);

  async function loadRuns() {
    setLoading(true);
    const params = new URLSearchParams();
    params.set("limit", String(limit));
    params.set("offset", String(offset));
    if (jobFilter) params.set("job_name", jobFilter);
    if (statusFilter) params.set("status", statusFilter);
    try {
      const data = await listRuns(`?${params.toString()}`);
      setRuns(data.runs ?? data ?? []);
      setTotal(data.total ?? data.runs?.length ?? data.length ?? 0);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  const hasNext = offset + limit < total;
  const hasPrev = offset > 0;

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
            className="text-[11px] uppercase tracking-[var(--tracking-nav)] px-3 py-2.5 font-medium text-ink-mute hover:text-ink transition-colors"
          >
            Settings
          </Link>
          <Link
            to="/admin/runs"
            className="text-[11px] uppercase tracking-[var(--tracking-nav)] px-3 py-2.5 font-medium text-ink border-b-2 border-ink"
          >
            Runs
          </Link>
        </div>
      </header>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-6 items-end">
        <div>
          <label className="block font-mono text-[10px] uppercase tracking-[0.22em] text-ink-mute font-semibold mb-1">
            Job Name
          </label>
          <input
            className="w-48 px-2.5 py-2 border border-ink bg-paper font-disp text-sm text-ink focus:outline-none focus:border-signal"
            value={jobFilter}
            onChange={(e) => {
              setJobFilter(e.target.value);
              setOffset(0);
            }}
            placeholder="Filter…"
          />
        </div>
        <div>
          <label className="block font-mono text-[10px] uppercase tracking-[0.22em] text-ink-mute font-semibold mb-1">
            Status
          </label>
          <select
            className="w-40 px-2.5 py-2 border border-ink bg-paper font-mono text-[11px] text-ink focus:outline-none focus:border-signal"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setOffset(0);
            }}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s || "All"}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={() => {
            setJobFilter("");
            setStatusFilter("");
            setOffset(0);
          }}
          className="font-mono text-[11px] uppercase tracking-[0.14em] font-semibold px-4 py-2 border border-ink text-ink hover:bg-paper-deep transition-colors"
        >
          Reset
        </button>
      </div>

      {/* Table */}
      {loading ? (
        <p className="font-disp text-sm text-ink-mute py-4">Loading…</p>
      ) : runs.length === 0 ? (
        <p className="font-disp text-sm text-ink-mute py-4">No runs found.</p>
      ) : (
        <div className="border border-ink mb-6">
          <div className="hidden sm:grid grid-cols-[1fr_100px_160px_80px_1fr] gap-0 bg-paper-deep border-b border-ink">
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
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-mute px-3 py-2 font-semibold">
              Error
            </span>
          </div>
          {runs.map((run) => (
            <div
              key={run.id}
              className="grid grid-cols-1 sm:grid-cols-[1fr_100px_160px_80px_1fr] gap-0 border-b border-hair last:border-b-0 hover:bg-paper-deep transition-colors"
            >
              <div className="px-3 py-2.5 flex flex-col justify-center">
                <span className="font-disp text-sm font-semibold text-ink truncate">
                  {run.job_name}
                </span>
              </div>
              <div className="px-3 py-2.5 flex items-center">
                <span
                  className={`font-mono text-[10px] uppercase tracking-[0.14em] font-semibold ${
                    run.status === "completed"
                      ? "text-ink"
                      : run.status === "failed"
                        ? "text-signal"
                        : "text-ink-mute"
                  }`}
                >
                  {run.status}
                </span>
              </div>
              <div className="px-3 py-2.5 flex items-center">
                <span className="font-mono text-[11px] text-ink-mute">
                  {formatDateTimeLocal(run.started_at)}
                </span>
              </div>
              <div className="px-3 py-2.5 flex items-center justify-end">
                <span className="font-mono text-[11px] text-ink tabular-nums">
                  {run.events_added ?? "—"}
                </span>
              </div>
              <div className="px-3 py-2.5 flex items-center">
                <span className="font-mono text-[11px] text-signal truncate">
                  {run.error || "—"}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <span className="font-mono text-[11px] text-ink-mute">
          {total > 0
            ? `${offset + 1}–${Math.min(offset + limit, total)} of ${total}`
            : "0 results"}
        </span>
        <div className="flex gap-2">
          <button
            onClick={() => setOffset((o) => Math.max(0, o - limit))}
            disabled={!hasPrev}
            className="font-mono text-[11px] uppercase tracking-[0.14em] font-semibold px-4 py-2 border border-ink text-ink hover:bg-paper-deep transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <button
            onClick={() => setOffset((o) => o + limit)}
            disabled={!hasNext}
            className="font-mono text-[11px] uppercase tracking-[0.14em] font-semibold px-4 py-2 border border-ink text-ink hover:bg-paper-deep transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      </div>
    </main>
  );
}
