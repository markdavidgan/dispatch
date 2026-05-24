interface Props {
  issueNo?: number | null;
  date?: string | null;
  filedAt?: string;
  durationSec?: number;
}

export default function Masthead({ issueNo, date, filedAt = "02:00:18", durationSec }: Props) {
  if (issueNo == null && !date) return null;
  const duration = durationSec
    ? `${Math.floor(durationSec / 60)}:${String(durationSec % 60).padStart(2, "0")}`
    : null;
  return (
    <div className="py-6 border-b border-hair-strong flex items-center justify-between gap-6 flex-wrap font-mono text-[11px] text-ink-soft tabular-nums tracking-[0.04em]">
      <div className="flex gap-4 flex-wrap items-center">
        <span>
          <span className="uppercase tracking-[0.14em] text-ink-mute mr-1.5">Filed</span>{" "}
          <span className="text-ink font-semibold">{filedAt} ⏵ AVA</span>
        </span>
        {date && (
          <span>
            <span className="uppercase tracking-[0.14em] text-ink-mute mr-1.5">Date</span>{" "}
            <span className="text-ink font-semibold">{date}</span>
          </span>
        )}
        {duration && (
          <span>
            <span className="uppercase tracking-[0.14em] text-ink-mute mr-1.5">Duration</span>{" "}
            <span className="text-ink font-semibold">{duration}</span>
          </span>
        )}
      </div>
    </div>
  );
}
