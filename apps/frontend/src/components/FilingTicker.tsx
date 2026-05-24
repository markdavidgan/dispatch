interface TickerRow {
  time: string;
  slug: string;
  isLatest?: boolean;
}

interface Props {
  rows: TickerRow[];
}

export default function FilingTicker({ rows }: Props) {
  if (rows.length === 0) return null;

  return (
    <>
      {/* Desktop: fixed left rail */}
      <aside className="hidden lg:block fixed left-0 top-[60px] bottom-0 w-24 border-r border-hair-strong bg-paper font-mono text-[10px] px-3 py-6 overflow-hidden z-10">
        <div className="text-[9px] uppercase tracking-[0.22em] text-ink-mute mb-4 font-semibold">
          Wire
        </div>
        {rows.map((r, i) => (
          <div
            key={`${r.time}-${r.slug}-${i}`}
            className={`flex flex-col py-1.5 border-t border-hair tabular-nums ${
              r.isLatest ? "border-signal" : ""
            }`}
          >
            <span
              className={`font-semibold text-[11px] ${r.isLatest ? "text-signal" : "text-ink"}`}
            >
              {r.time}
            </span>
            <span className="text-ink-mute uppercase tracking-[0.06em] text-[9px] mt-0.5">
              {r.slug}
            </span>
          </div>
        ))}
      </aside>

      {/* Mobile: horizontal scroll strip */}
      <aside className="block lg:hidden border-b border-hair-strong bg-paper font-mono text-[10px] z-10">
        <div className="flex items-center gap-3 px-4 py-3 overflow-x-auto scrollbar-hide">
          <span className="text-[9px] uppercase tracking-[0.22em] text-ink-mute font-semibold shrink-0">
            Wire
          </span>
          {rows.map((r, i) => (
            <div
              key={`m-${r.time}-${r.slug}-${i}`}
              className={`flex items-center gap-2 shrink-0 px-2 py-1 border-l border-hair tabular-nums ${
                r.isLatest ? "border-l-signal" : ""
              }`}
            >
              <span
                className={`font-semibold text-[11px] ${
                  r.isLatest ? "text-signal" : "text-ink"
                }`}
              >
                {r.time}
              </span>
              <span className="text-ink-mute uppercase tracking-[0.06em] text-[9px]">
                {r.slug}
              </span>
            </div>
          ))}
        </div>
      </aside>
    </>
  );
}
