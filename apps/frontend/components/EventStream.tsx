import type { SnapshotEvent } from "@/lib/snapshot";

interface Props {
  events: SnapshotEvent[];
  limit?: number;
}

export default function EventStream({ events, limit = 20 }: Props) {
  const rows = events.slice(0, limit);
  return (
    <section className="mb-14">
      <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink pb-3.5 border-b border-ink font-semibold mb-6 flex justify-between">
        Recent events<span className="text-ink-mute font-normal">Last {rows.length}</span>
      </h2>
      {rows.length === 0 ? (
        <p className="font-disp text-base text-ink-soft italic">Quiet project. No movement in the ingest window.</p>
      ) : (
        <div>
          {rows.map((ev) => (
            <div
              key={`${ev.project_slug}-${ev.external_id}`}
              className="grid grid-cols-[84px_110px_1fr_24px] gap-3.5 items-baseline py-2.5 border-b border-hair font-mono text-xs hover:bg-paper-deep"
            >
              <span className="text-ink tabular-nums font-medium">{ev.occurred_at?.split("T")[1]?.slice(0, 5) ?? "—"}</span>
              <span className="text-[10px] uppercase tracking-[0.18em] text-signal font-semibold">{ev.kind}</span>
              <span className="font-disp text-sm text-ink font-medium">{ev.title}</span>
              {ev.url && (
                <a className="text-ink-mute text-right hover:text-signal" href={ev.url} target="_blank" rel="noreferrer">
                  ↗
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
