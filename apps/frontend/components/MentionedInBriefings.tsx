import Link from "next/link";

interface Mention {
  date: string; // YYYY-MM-DD
  excerpt: string;
  issue_no?: number | null;
}

interface Props {
  mentions: Mention[];
}

export default function MentionedInBriefings({ mentions }: Props) {
  return (
    <section className="mb-14">
      <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink pb-3.5 border-b border-ink font-semibold mb-6 flex justify-between">
        Mentioned in briefings<span className="text-ink-mute font-normal">Last 5</span>
      </h2>
      {mentions.length === 0 ? (
        <p className="font-disp text-base text-ink-soft italic">
          This project hasn&apos;t appeared in any briefing yet.
        </p>
      ) : (
        <ul>
          {mentions.map((m) => (
            <li key={m.date}>
              <Link
                href={`/briefings/${m.date}`}
                className="grid grid-cols-[88px_1fr_28px] gap-5 items-center py-4.5 border-b border-hair hover:pl-2 transition-[padding] duration-150 group"
              >
                <span>
                  {m.issue_no != null && (
                    <span className="block font-mono text-[11px] tracking-[0.14em] text-signal uppercase font-semibold tabular-nums">
                      ISS-{String(m.issue_no).padStart(3, "0")}
                    </span>
                  )}
                  <span className="block font-mono text-[9.5px] tracking-[0.18em] text-ink-mute uppercase mt-1">
                    {new Date(`${m.date}T00:00:00Z`).toUTCString().slice(5, 16)}
                  </span>
                </span>
                <span className="font-disp text-lg leading-[1.4] text-ink font-medium tracking-[-0.005em]">{m.excerpt}</span>
                <span className="font-mono text-sm text-ink-mute text-right group-hover:text-signal group-hover:translate-x-1 transition-transform duration-150">→</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
