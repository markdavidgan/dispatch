import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchPodcasts, fetchPodcastEpisodes, fetchSetupStatus } from "@/lib/api";
import { PodcastSubscribeBlock } from "@/components/PodcastSubscribeBlock";

interface Podcast {
  project_slug: string;
  title: string;
  description: string;
  enabled: boolean;
  feed_url: string;
  episode_count?: number;
  last_published_at?: string | null;
}

interface Status {
  notebooklm?: boolean;
  tts?: boolean;
  ai?: boolean;
  ai_provider?: string | null;
  storage_provider?: string | null;
}

const STATUS_ROWS: { key: keyof Status; label: string; need: string }[] = [
  { key: "notebooklm", label: "NotebookLM session", need: "podcast.notebooklm_session" },
  { key: "ai",         label: "AI provider",         need: "ai.provider + ANTHROPIC_API_KEY / KIMI_OAUTH_JSON" },
  { key: "tts",        label: "Google Cloud TTS",    need: "GOOGLE_APPLICATION_CREDENTIALS" },
];

export default function PodcastsPage() {
  const [podcasts, setPodcasts] = useState<Podcast[]>([]);
  const [episodesBySlug, setEpisodesBySlug] = useState<Record<string, any[]>>({});
  const [status, setStatus] = useState<Status>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [pData, sData] = await Promise.all([fetchPodcasts(), fetchSetupStatus()]);
        const list: Podcast[] = (pData.podcasts ?? []).filter((p: Podcast) => p.enabled);
        // dispatch-weekly first
        list.sort((a, b) =>
          a.project_slug === "dispatch-weekly" ? -1 : b.project_slug === "dispatch-weekly" ? 1 : 0,
        );
        setPodcasts(list);
        setStatus(sData ?? {});
        const eps: Record<string, any[]> = {};
        await Promise.all(
          list.map(async (p) => {
            try {
              const r = await fetchPodcastEpisodes(p.project_slug);
              eps[p.project_slug] = r.episodes ?? [];
            } catch {
              eps[p.project_slug] = [];
            }
          }),
        );
        setEpisodesBySlug(eps);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <main className="lg:pl-24">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-24 text-center">
          <p className="font-disp text-base text-ink-soft">Loading…</p>
        </div>
      </main>
    );
  }

  const featured = podcasts.find((p) => p.project_slug === "dispatch-weekly") ?? podcasts[0];
  const others = podcasts.filter((p) => p.project_slug !== featured?.project_slug);

  return (
    <main className="lg:pl-24">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-12">
        <section className="pb-6 border-b border-ink mb-8">
          <h1 className="font-disp text-[42px] font-extrabold leading-[1.05] tracking-[-0.025em]">
            Podcast
          </h1>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-mute mt-2.5">
            Weekly · NotebookLM composes · GCP narrates
          </p>
        </section>

        {!featured ? (
          <p className="font-disp text-base text-ink-soft italic">
            No podcasts configured yet. Enable a podcast under{" "}
            <Link to="/admin/settings" className="text-ink underline">admin / settings</Link>.
          </p>
        ) : (
          <>
            <article className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-12 pb-12 border-b border-hair-strong">
              <div>
                <Link
                  to={`/podcast/${featured.project_slug}`}
                  className="font-disp text-[36px] font-extrabold leading-tight tracking-[-0.025em] text-ink hover:text-signal block"
                >
                  {featured.title}
                </Link>
                {featured.description && (
                  <p className="font-disp text-lg leading-[1.5] text-ink-soft mt-3 max-w-[680px]">
                    {featured.description}
                  </p>
                )}
                <div className="font-mono text-[10.5px] uppercase tracking-[0.18em] text-ink-mute mt-4 flex gap-3 flex-wrap">
                  <span>
                    <span className="text-ink font-semibold">
                      {episodesBySlug[featured.project_slug]?.filter((e) => e.status === "ready").length ?? 0}
                    </span>{" "}episodes
                  </span>
                  {featured.last_published_at && (
                    <>
                      <span className="text-hair-strong">·</span>
                      <span>Latest filed {featured.last_published_at.slice(0, 10)}</span>
                    </>
                  )}
                  <span className="text-hair-strong">·</span>
                  <Link
                    to={`/podcast/${featured.project_slug}`}
                    className="text-ink hover:text-signal font-semibold"
                  >
                    Episodes →
                  </Link>
                </div>
                <PodcastSubscribeBlock feedUrl={featured.feed_url} title={featured.title} />
              </div>

              {/* Credentials / backend services panel */}
              <aside className="border border-ink p-5">
                <h3 className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink font-semibold pb-3 mb-3 border-b border-hair-strong">
                  Backend services
                </h3>
                <ul className="space-y-3 text-[12.5px]">
                  {STATUS_ROWS.map((row) => {
                    const ok = !!status[row.key];
                    return (
                      <li key={row.key} className="grid grid-cols-[8px_1fr] gap-3 items-start">
                        <span
                          className={`mt-1.5 w-2 h-2 rounded-full ${ok ? "bg-signal" : "bg-hair-strong"}`}
                          aria-hidden
                        />
                        <span>
                          <span className="font-disp font-semibold text-ink block">{row.label}</span>
                          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-mute block mt-0.5">
                            {ok ? "configured" : "not configured"}
                          </span>
                          <span className="font-mono text-[10px] text-ink-mute block mt-1 break-all">{row.need}</span>
                        </span>
                      </li>
                    );
                  })}
                </ul>
                <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink-mute mt-4 pt-4 border-t border-hair">
                  Configure under{" "}
                  <Link to="/admin/settings" className="text-ink underline">admin / settings</Link>.
                </p>
              </aside>
            </article>

            {others.length > 0 && (
              <section className="pt-12">
                <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink pb-3.5 border-b border-ink font-semibold mb-6">
                  Per-project feeds
                </h2>
                <div className="space-y-10">
                  {others.map((p) => (
                    <article key={p.project_slug} className="border-b border-hair pb-8 last:border-b-0">
                      <Link
                        to={`/podcast/${p.project_slug}`}
                        className="font-disp text-[22px] font-bold leading-tight tracking-[-0.02em] text-ink hover:text-signal"
                      >
                        {p.title}
                      </Link>
                      {p.description && (
                        <p className="font-disp text-base leading-[1.5] text-ink-soft mt-2 max-w-[680px]">
                          {p.description}
                        </p>
                      )}
                      <PodcastSubscribeBlock feedUrl={p.feed_url} title={p.title} />
                    </article>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}
