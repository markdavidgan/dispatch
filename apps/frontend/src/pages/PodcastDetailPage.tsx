import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchPodcasts, fetchPodcastEpisodes } from "@/lib/api";
import { EpisodeCard } from "@/components/EpisodeCard";
import { PodcastSubscribeBlock } from "@/components/PodcastSubscribeBlock";

export default function PodcastDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const [meta, setMeta] = useState<any>(null);
  const [episodes, setEpisodes] = useState<any[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      if (!slug) return;
      try {
        const [podcastsData, epsData] = await Promise.all([
          fetchPodcasts(),
          fetchPodcastEpisodes(slug),
        ]);
        const podcasts = podcastsData.podcasts ?? [];
        setMeta(podcasts.find((p: any) => p.project_slug === slug) ?? null);
        setEpisodes(epsData.episodes ?? []);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [slug]);

  if (loading) {
    return (
      <main className="lg:pl-24">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-24 text-center">
          <p className="font-disp text-base text-ink-soft">Loading…</p>
        </div>
      </main>
    );
  }

  if (!meta && (!episodes || episodes.length === 0)) {
    return (
      <main className="lg:pl-24">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-24 text-center">
          <p className="font-disp text-base text-ink-soft">Podcast not found.</p>
        </div>
      </main>
    );
  }

  const title = meta?.title ?? slug;
  const description = meta?.description ?? "";
  const feedUrl = meta?.feed_url ?? "";
  const eps = episodes ?? [];
  const ready = eps.filter((e) => e.status === "ready");

  return (
    <main className="lg:pl-24">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-12">
        <section className="pb-6 border-b border-ink mb-8">
          <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-mute mb-3">
            <Link to="/podcasts" className="hover:text-signal">
              Podcasts
            </Link>{" "}
            · {title}
          </div>
          <h1 className="font-disp text-[56px] font-extrabold leading-[1.05] tracking-[-0.025em]">
            {title}
          </h1>
          {description && (
            <p className="font-disp text-lg leading-[1.5] text-ink-soft mt-3 max-w-[760px]">
              {description}
            </p>
          )}
          <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-mute mt-4 flex gap-3 flex-wrap">
            <span>
              <span className="text-ink font-semibold">{ready.length}</span> ready
            </span>
            {ready.length !== eps.length && (
              <>
                <span className="text-hair-strong">·</span>
                <span>
                  <span className="text-ink font-semibold">{eps.length}</span> total
                </span>
              </>
            )}
            {eps[0]?.published_at && (
              <>
                <span className="text-hair-strong">·</span>
                <span>Latest filed {eps[0].published_at.slice(0, 10)}</span>
              </>
            )}
          </div>
        </section>

        <PodcastSubscribeBlock feedUrl={feedUrl} title={title} />

        <section className="mt-12">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink pb-3.5 border-b border-ink font-semibold mb-2 flex justify-between">
            Episodes
            <span className="text-ink-mute font-normal">
              {eps.length} total
            </span>
          </h2>
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
    </main>
  );
}
