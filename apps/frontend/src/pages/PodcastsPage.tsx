import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchPodcasts, fetchPodcastEpisodes, fetchSetupStatus } from "@/lib/api";
import Seo from "@/components/Seo";
import { EpisodeCard } from "@/components/EpisodeCard";
import { PodcastSubscribeBlock } from "@/components/PodcastSubscribeBlock";

interface Podcast {
  project_slug: string;
  title: string;
  description: string;
  enabled: boolean;
  feed_url: string;
  episode_count?: number;
  last_published_at?: string | null;
  auth?: { username: string; password: string } | null;
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
  const [episodes, setEpisodes] = useState<any[] | null>(null);
  const [status, setStatus] = useState<Status>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const pData = await fetchPodcasts();
        const list: Podcast[] = (pData.podcasts ?? []).filter((p: Podcast) => p.enabled);
        // dispatch-weekly first
        list.sort((a, b) =>
          a.project_slug === "dispatch-weekly" ? -1 : b.project_slug === "dispatch-weekly" ? 1 : 0,
        );
        setPodcasts(list);

        const featured = list.find((p) => p.project_slug === "dispatch-weekly") ?? list[0];
        if (featured) {
          const r = await fetchPodcastEpisodes(featured.project_slug);
          setEpisodes(r.episodes ?? []);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }

      // Backend status panel is best-effort; don't block podcast display
      try {
        const sData = await fetchSetupStatus();
        setStatus(sData ?? {});
      } catch {
        setStatus({});
      }
    }
    load();
  }, [])

  if (loading) {
    return (
      <>
        <Seo title="Podcast" canonicalPath="/podcast" />
        <main className="lg:pl-24">
          <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-24 text-center">
            <p className="font-disp text-base text-ink-soft">Loading…</p>
          </div>
        </main>
      </>
    );
  }

  const featured = podcasts.find((p) => p.project_slug === "dispatch-weekly") ?? podcasts[0];
  const others = podcasts.filter((p) => p.project_slug !== featured?.project_slug);
  const eps = episodes ?? [];
  const ready = eps.filter((e) => e.status === "ready");

  return (
    <>
      <Seo
        title="Podcast"
        description="Weekly AI-generated podcast episodes — cross-project digests and per-repo overviews."
        canonicalPath="/podcast"
      />
      <main className="lg:pl-24">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-12">
        <section className="pb-6 border-b border-ink mb-8">
          <h1 className="font-disp text-[42px] font-extrabold leading-[1.05] tracking-[-0.025em]">
            Podcast
          </h1>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-mute mt-2.5">
            Weekly · NotebookLM dialog overviews
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
                <h2 className="font-disp text-[36px] font-extrabold leading-tight tracking-[-0.025em] text-ink">
                  {featured.title}
                </h2>
                {featured.description && (
                  <p className="font-disp text-lg leading-[1.5] text-ink-soft mt-3 max-w-[680px]">
                    {featured.description}
                  </p>
                )}
                <div className="font-mono text-[10.5px] uppercase tracking-[0.18em] text-ink-mute mt-4 flex gap-3 flex-wrap">
                  <span>
                    <span className="text-ink font-semibold">{ready.length}</span>{" "}
                    {ready.length === 1 ? "episode" : "episodes"}
                  </span>
                  {featured.last_published_at && (
                    <>
                      <span className="text-hair-strong">·</span>
                      <span>Latest filed {featured.last_published_at.slice(0, 10)}</span>
                    </>
                  )}
                </div>
                <PodcastSubscribeBlock
                  feedUrl={featured.feed_url}
                  title={featured.title}
                  auth={featured.auth ?? undefined}
                />

                {/* Episodes list */}
                <section className="mt-12">
                  <h3 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink pb-3.5 border-b border-ink font-semibold mb-2 flex justify-between">
                    Episodes
                    <span className="text-ink-mute font-normal">
                      {eps.length} total
                    </span>
                  </h3>
                  {eps.length === 0 ? (
                    <p className="font-disp text-base text-ink-soft italic mt-6">
                      No episodes filed yet. The weekly cron fires Saturday 05:00 local.
                    </p>
                  ) : (
                    <ul>
                      {eps.map((e) => (
                        <li key={e.id}>
                          <EpisodeCard episode={e} />
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              </div>

              {/* Credentials / backend services panel */}
              <aside className="border border-ink p-5 h-fit">
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
    </>
  );
}
