import { Link } from "react-router-dom";

interface Props {
  issueNo: number;
  date: string;
  activeCount: number;
  heldCount: number;
  eventsToday: number;
  weekNo: number;
  linkable?: boolean;
}

export default function Numeral({
  issueNo,
  date,
  activeCount,
  heldCount,
  eventsToday,
  weekNo,
  linkable = true,
}: Props) {
  const numeralText = String(issueNo).padStart(3, "0");
  const numeralClass =
    "font-disp text-[96px] sm:text-[200px] leading-[0.85] font-extrabold tracking-[-0.06em] text-ink tabular-nums inline-block";
  return (
    <div
      className="relative mb-12"
      style={{ animation: "numeral-in 800ms cubic-bezier(.16,.84,.36,1) both" }}
    >
      <div className="font-mono text-[10px] uppercase tracking-[var(--tracking-meta)] text-ink-mute mb-2 font-semibold flex items-center gap-2.5">
        <span className="w-1.5 h-1.5 rounded-full bg-signal" /> Issue / Today
      </div>
      {linkable ? (
        <Link
          to={`/briefings/${date}`}
          aria-label={`View Issue No. ${issueNo} — briefing filed ${date}`}
          className={`${numeralClass} hover:text-signal transition-colors`}
        >
          {numeralText}
        </Link>
      ) : (
        <span className={numeralClass}>{numeralText}</span>
      )}
      <div className="absolute right-0 top-[30px] font-mono text-[11px] uppercase tracking-[0.14em] text-ink-mute leading-[1.7] text-right tabular-nums">
        <div>
          <span className="text-ink font-semibold">{String(activeCount).padStart(2, "0")}</span> active
        </div>
        <div>
          <span className="text-ink font-semibold">{String(heldCount).padStart(2, "0")}</span> held
        </div>
        <div>
          <span className="text-ink font-semibold">{eventsToday}</span> events today
        </div>
        <div>
          WK <span className="text-ink font-semibold">{weekNo}</span>
        </div>
      </div>
    </div>
  );
}
