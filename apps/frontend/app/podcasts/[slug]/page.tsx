import Link from "next/link";
import { notFound } from "next/navigation";
import { EpisodeCard } from "@/components/EpisodeCard";
import { PodcastSubscribeBlock } from "@/components/PodcastSubscribeBlock";

const API_URL = process.env.DISPATCH_API_URL || "http://localhost:10060";

export const revalidate = 300;

interface PodcastSummary {
  project_slug: string;
  title: string;
  description: string;
  enabled: boolean;
  feed_url: string;
  episode_count?: number;
  last_published_at?: string | null;
}

interface Episode {
  id: string;
  episode_no: number;
  week_start: string;
  title: string;
  audio_key: string | null;
  duration_seconds: number | null;
  status: string;
  published_at: string | null;
}

function cfHeaders() {
  const id = process.env.CF_ACCESS_CLIENT_ID;
  const sec = process.env.CF_ACCESS_CLIENT_SECRET;
  return id && sec
    ? { "CF-Access-Client-Id": id, "CF-Access-Client-Secret": sec }
    : null;
}

async function fetchPodcastMetadata(slug: string): Promise<PodcastSummary | null> {
  const headers = cfHeaders();
  if (!headers) return null;
  try {
    const r = await fetch(`${API_URL}/podcasts`, {
      headers,
      next: { revalidate: 300 },
    });
    if (!r.ok) return null;
    const data = await r.json();
    return (data.podcasts ?? []).find(
      (p: PodcastSummary) => p.project_slug === slug
    ) ?? null;
  } catch {
    return null;
  }
}

async function fetchPodcastEpisodes(slug: string): Promise<Episode[] | null> {
  const headers = cfHeaders();
  if (!headers) return null;
  try {
    const r = await fetch(`${API_URL}/podcasts/${slug}/episodes`, {
      headers,
      next: { revalidate: 300 },
    });
    if (!r.ok) return null;
    const data = await r.json();
    return data.episodes ?? [];
  } catch {
    return null;
  }
}

function podcastAuth() {
  const username = process.env.PODCAST_AUTH_USERNAME ?? "";
  const password = process.env.PODCAST_AUTH_PASSWORD ?? "";
  if (!username && !password) return undefined;
  return { username, password };
}

export default async function PodcastPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const [meta, episodes] = await Promise.all([
    fetchPodcastMetadata(slug),
    fetchPodcastEpisodes(slug),
  ]);

  if (!meta && (!episodes || episodes.length === 0)) {
    notFound();
  }

  const title = meta?.title ?? slug;
  const description = meta?.description ?? "";
  const feedUrl =
    meta?.feed_url ??
    `${process.env.PODCAST_BASE_URL ?? ""}/${slug}.xml`;
  const auth = podcastAuth();
  const eps = episodes ?? [];
  const ready = eps.filter((e) => e.status === "ready");

  return (
    <main className="lg:pl-24">
      <div className="max-w-[1400px] mx-auto px-4 sm:px-8 py-12">
        <section className="pb-6 border-b border-ink mb-8">
          <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-mute mb-3">
            <Link href="/podcasts" className="hover:text-signal">
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

        <PodcastSubscribeBlock feedUrl={feedUrl} title={title} auth={auth} />

        <section className="mt-12">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.22em] text-ink pb-3.5 border-b border-ink font-semibold mb-2 flex justify-between">
            Episodes
            <span className="text-ink-mute font-normal">
              {eps.length} total
            </span>
          </h2>
          {eps.length === 0 ? (
            <p className="font-disp text-base text-ink-soft italic mt-6">
              No episodes filed yet. The weekly cron fires Monday 06:00 local.
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
