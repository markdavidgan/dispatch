import { fetchSnapshot } from "@/lib/snapshot";
import { fetchLive } from "@/lib/live";
import Masthead from "@/components/Masthead";
import Numeral from "@/components/Numeral";
import LeadHero from "@/components/LeadHero";
import Addendum from "@/components/Addendum";
import ProjectList from "@/components/ProjectList";
import AudioPlayer from "@/components/AudioPlayer";
import RefreshButton from "@/components/RefreshButton";
import FilingTicker from "@/components/FilingTicker";
import Link from "next/link";

export const revalidate = 300;

function isoWeek(dateStr: string): number {
  // ISO 8601 week number from YYYY-MM-DD.
  const d = new Date(`${dateStr}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
}

export default async function HomePage() {
  const snapshot = await fetchSnapshot();
  const live = await fetchLive();
  const brief = snapshot?.brief;

  if (!brief) {
    // No ticker is rendered in the empty state, so don't reserve its column.
    return (
      <main className="max-w-[1400px] mx-auto px-4 sm:px-8 py-24 text-center">
        <p className="font-disp text-base text-ink-soft">
          The newsroom hasn't filed yet. Check back after the 02:00 synthesis.
        </p>
      </main>
    );
  }

  const counts = {
    active: brief.projects.filter((p) => p.status === "active").length,
    held:   brief.projects.filter((p) => p.status === "held").length,
  };

  const tickerRows = (snapshot?.recent_events ?? []).slice(0, 12).map((e, i) => ({
    time: e.occurred_at?.split("T")[1]?.slice(0, 5) ?? "—",
    slug: e.project_slug,
    isLatest: i === 0,
  }));

  return (
    <>
      <div className="lg:pl-24">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-8">
          <Masthead
            issueNo={brief.issue_no}
            date={brief.date}
            filedAt={brief.filed_at ?? "02:00:18"}
            durationSec={brief.audio?.lead_duration_s ?? undefined}
          />
          {/* Ticker: desktop fixed left rail (viewport-relative), mobile scroll strip below masthead */}
          <FilingTicker rows={tickerRows} />
          <div className="flex items-center justify-end gap-3 py-2">
            <AudioPlayer
              leadUrl={brief.audio?.lead_url}
              addendumUrl={brief.audio?.addendum_url}
              durationLabel={brief.audio?.lead_duration_s ? `${brief.audio.lead_duration_s}s` : undefined}
            />
            <RefreshButton />
          </div>

          <main className="pt-12 pb-24 grid grid-cols-1 lg:grid-cols-[minmax(0,8fr)_minmax(0,3fr)] gap-16">
            <article>
              <Numeral
                issueNo={brief.issue_no}
                date={brief.date}
                activeCount={counts.active}
                heldCount={counts.held}
                eventsToday={snapshot?.recent_events?.length ?? 0}
                weekNo={isoWeek(brief.date)}
              />
              <LeadHero headline={brief.lead_headline} body={brief.lead_body} />
              {brief.addendums?.map((a, i) => (
                <Addendum key={`${a.filed_at}-${i}`} label={a.label} body={a.body} />
              ))}
              <ProjectList projects={brief.projects} liveStats={live?.projects} />
            </article>

            <aside className="font-disp text-sm">
              <section className="mb-12">
                <h3 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink pb-3 border-b border-ink mb-4.5 font-semibold flex justify-between">
                  Today<span className="font-normal text-ink-mute">{brief.date.slice(5).replace("-", "·")}</span>
                </h3>
                <div className="grid grid-cols-2 border-t border-b border-hair">
                  <Cell n={String(snapshot?.recent_events?.length ?? 0)} l="Events" />
                  <Cell n={String(counts.active)}                       l="Projects" />
                </div>
              </section>

              {snapshot?.episodes?.[0] && (
                <section className="mb-12">
                  <h3 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink pb-3 border-b border-ink mb-4.5 font-semibold flex justify-between">
                    Latest Transmission<span className="font-normal text-ink-mute">Podcast</span>
                  </h3>
                  <div className="font-mono text-[64px] font-bold leading-[0.95] tracking-[-0.03em] text-ink tabular-nums">
                    {String(snapshot.episodes[0].episode_no ?? 0).padStart(3, "0")}
                  </div>
                  {snapshot.episodes[0].podcast_title ? (
                    <>
                      <div className="font-disp text-lg font-semibold leading-tight mt-2 mb-1">{snapshot.episodes[0].podcast_title}</div>
                      <div className="font-mono text-[10.5px] uppercase tracking-[0.18em] text-ink-mute mb-4">{snapshot.episodes[0].title}</div>
                    </>
                  ) : (
                    <div className="font-disp text-lg font-semibold leading-tight mt-2 mb-4">{snapshot.episodes[0].title}</div>
                  )}
                </section>
              )}

              <section>
                <Link
                  href="/briefings"
                  className="flex items-baseline justify-between py-4.5 border-t border-b border-ink font-disp text-lg font-semibold tracking-[-0.01em] text-ink hover:text-signal"
                >
                  All Briefings <span className="font-mono text-[11px] tracking-[0.14em] text-ink-mute font-normal tabular-nums">{brief.issue_no} →</span>
                </Link>
              </section>
            </aside>
          </main>
        </div>
      </div>
    </>
  );
}

function Cell({ n, l }: { n: string; l: string }) {
  return (
    <div className="py-3.5 border-r border-hair-strong last:border-r-0 last:pl-4.5">
      <div className="font-disp text-[32px] font-bold leading-none tabular-nums">{n}</div>
      <div className="font-mono text-[9.5px] uppercase tracking-[0.22em] text-ink-mute mt-1.5 font-medium">{l}</div>
    </div>
  );
}
