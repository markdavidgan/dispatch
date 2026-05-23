import Link from "next/link";
import { fetchBriefings } from "@/lib/briefings";

export const revalidate = 300;

export default async function BriefingsPage() {
  const briefings = await fetchBriefings();

  return (
    <main className="lg:pl-24">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-12">
        <section className="pb-6 border-b border-ink mb-8">
          <h1 className="font-disp text-[42px] font-extrabold leading-[1.05] tracking-[-0.025em]">Briefings</h1>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-mute mt-2.5">
            The archive · {briefings.length} filed
          </p>
        </section>

        {briefings.length === 0 ? (
          <p className="font-disp text-base text-ink-soft italic">
            The newsroom hasn&apos;t filed yet. Check back after the 02:00 synthesis.
          </p>
        ) : (
          <ul>
            {briefings.map((b) => (
              <li key={b.date}>
                <Link
                  href={`/briefings/${b.date}`}
                  className="grid grid-cols-[72px_1fr] sm:grid-cols-[120px_1fr_140px] gap-x-4 sm:gap-x-6 gap-y-1 sm:gap-y-0 items-start sm:items-baseline py-5 border-b border-hair hover:bg-paper-deep"
                >
                  <span className="font-mono text-[11px] uppercase tracking-[0.14em] text-signal font-semibold tabular-nums row-start-1 col-start-1">
                    #{String(b.issue_no).padStart(3, "0")}
                    <span className="block text-[9.5px] tracking-[0.18em] text-ink-mute uppercase mt-1 font-normal">
                      {b.date}
                    </span>
                  </span>
                  <span className="font-disp text-lg leading-[1.35] font-medium tracking-[-0.005em] text-ink row-start-1 col-start-2">
                    {b.lead_headline}
                  </span>
                  <span className="font-mono text-[10.5px] uppercase tracking-[0.18em] text-ink-mute font-medium sm:text-right row-start-2 col-start-2 sm:row-start-1 sm:col-start-3">
                    {b.active_count} projects · {b.filed_at}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
