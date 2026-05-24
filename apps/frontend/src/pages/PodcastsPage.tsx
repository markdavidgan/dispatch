import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchPodcasts } from "@/lib/api";
import { PodcastSubscribeBlock } from "@/components/PodcastSubscribeBlock";

export default function PodcastsPage() {
  const [podcasts, setPodcasts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchPodcasts();
        setPodcasts(data.podcasts ?? []);
      } catch (e) {
        console.error(e);
        setPodcasts([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const active = podcasts.filter((p) => p.enabled);

  if (loading) {
    return (
      <main className="lg:pl-24">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-24 text-center">
          <p className="font-disp text-base text-ink-soft">Loading…</p>
        </div>
      </main>
    );
  }

  return (
    <main className="lg:pl-24">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-12">
        <section className="pb-6 border-b border-ink mb-8">
          <h1 className="font-disp text-[42px] font-extrabold leading-[1.05] tracking-[-0.025em]">
            Podcasts
          </h1>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-mute mt-2.5">
            {active.length} private feed{active.length === 1 ? "" : "s"} ·
            {" "}weekly NotebookLM bulletins
          </p>
        </section>

        {active.length === 0 ? (
          <p className="font-disp text-base text-ink-soft italic">
            No podcasts configured yet. Enable a project's podcast config in admin settings to publish one.
          </p>
        ) : (
          <div className="space-y-12">
            {active.map((p) => (
              <article key={p.project_slug} className="border-b border-hair-strong pb-12">
                <header className="grid grid-cols-[1fr_auto] gap-6 items-baseline">
                  <div>
                    <Link
                      to={`/podcasts/${p.project_slug}`}
                      className="font-disp text-[28px] font-bold leading-tight tracking-[-0.02em] text-ink hover:text-signal"
                    >
                      {p.title}
                    </Link>
                    {p.description && (
                      <p className="font-disp text-base leading-[1.55] text-ink-soft mt-2.5 max-w-[680px]">
                        {p.description}
                      </p>
                    )}
                    <div className="font-mono text-[10.5px] uppercase tracking-[0.18em] text-ink-mute mt-3 flex gap-3 flex-wrap">
                      {typeof p.episode_count === "number" && (
                        <span>
                          <span className="text-ink font-semibold">{p.episode_count}</span> episodes
                        </span>
                      )}
                      {p.last_published_at && (
                        <>
                          <span className="text-hair-strong">·</span>
                          <span>Latest filed {p.last_published_at.slice(0, 10)}</span>
                        </>
                      )}
                      <span className="text-hair-strong">·</span>
                      <Link
                        to={`/podcasts/${p.project_slug}`}
                        className="text-ink hover:text-signal font-semibold"
                      >
                        Episodes →
                      </Link>
                    </div>
                  </div>
                </header>
                <PodcastSubscribeBlock feedUrl={p.feed_url} title={p.title} />
              </article>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
