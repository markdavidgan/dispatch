import { useEffect, useState } from "react";
import { Link, useParams, Navigate } from "react-router-dom";
import { fetchBriefing } from "@/lib/api";
import Masthead from "@/components/Masthead";
import Numeral from "@/components/Numeral";
import LeadHero from "@/components/LeadHero";
import LeadArticle from "@/components/LeadArticle";
import Addendum from "@/components/Addendum";
import ProjectList from "@/components/ProjectList";
import AudioPlayer from "@/components/AudioPlayer";

function isoWeek(dateStr: string): number {
  const d = new Date(`${dateStr}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
}

export default function BriefingDetailPage() {
  const { date } = useParams<{ date: string }>();
  const [brief, setBrief] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      if (!date) {
        setLoading(false);
        return;
      }
      try {
        const data = await fetchBriefing(date);
        setBrief(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [date]);

  if (loading) {
    return (
      <main className="lg:pl-24">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-24 text-center">
          <p className="font-disp text-base text-ink-soft">Loading…</p>
        </div>
      </main>
    );
  }

  if (!brief) {
    return <Navigate to="/briefings" replace />;
  }

  const projects = brief.projects as Parameters<typeof ProjectList>[0]["projects"];
  const active = projects.filter((p: any) => p.status === "active").length;
  const held = projects.filter((p: any) => p.status === "held").length;

  return (
    <main className="lg:pl-24">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-8">
        <div className="pt-8 flex items-center justify-between gap-4">
          <Link
            to="/briefings"
            className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-mute hover:text-signal"
          >
            ← Briefings
          </Link>
          <AudioPlayer leadUrl={brief.audio_lead_url} addendumUrl={brief.audio_addendum_url} />
        </div>
        <Masthead issueNo={brief.issue_no} date={brief.date} filedAt={brief.filed_at} />
        <main className="pt-12 pb-24 grid grid-cols-1 lg:grid-cols-[minmax(0,8fr)_minmax(0,3fr)] gap-16">
          <article>
            <Numeral
              issueNo={brief.issue_no}
              date={brief.date}
              activeCount={active}
              heldCount={held}
              eventsToday={brief.recent_events.length}
              weekNo={isoWeek(brief.date)}
              linkable={false}
            />
            {brief.lead_article ? (
              <LeadArticle
                headline={brief.lead_headline}
                dek={brief.lead_body}
                article={brief.lead_article}
              />
            ) : (
              <LeadHero headline={brief.lead_headline} body={brief.lead_body} />
            )}
            {brief.addendums.map((a: any, i: number) => (
              <Addendum key={i} label={a.label} body={a.body} />
            ))}
            <ProjectList projects={projects} />

            <section className="mt-16 pt-5 border-t border-ink">
              <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink pb-3.5 font-semibold">
                Recent events for this day
              </h2>
              {brief.recent_events.map((e: any) => (
                <div
                  key={`${e.project_slug}-${e.external_id}`}
                  className="flex flex-wrap sm:grid sm:grid-cols-[84px_110px_1fr_24px] gap-x-3.5 gap-y-1 items-baseline py-2.5 border-b border-hair font-mono text-xs"
                >
                  <span className="text-ink tabular-nums font-medium shrink-0 w-[52px] sm:w-auto">
                    {e.occurred_at?.split("T")[1]?.slice(0, 5) ?? "—"}
                  </span>
                  <span className="text-[10px] uppercase tracking-[0.18em] text-signal font-semibold shrink-0 w-[80px] sm:w-auto">
                    {e.kind}
                  </span>
                  <span className="font-disp text-sm text-ink font-medium grow min-w-0 basis-full sm:basis-auto">
                    {e.title}
                  </span>
                  {e.url && (
                    <a
                      className="text-ink-mute hover:text-signal ml-auto sm:ml-0 sm:text-right"
                      href={e.url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      ↗
                    </a>
                  )}
                </div>
              ))}
            </section>
          </article>
        </main>
      </div>
    </main>
  );
}
