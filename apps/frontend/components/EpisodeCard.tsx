"use client";

interface Episode {
  id: string;
  episode_no: number;
  week_start: string;       // YYYY-MM-DD
  title: string;
  audio_key: string | null; // R2 key, e.g. "podcast/aether-focus/episode-001-2026-05-11.mp3"
  duration_seconds: number | null;
  status: string;
  published_at: string | null;
}

interface Props {
  episode: Episode;
}

/**
 * Episode row + native audio player. Audio streams through the dispatch
 * frontend's /api/audio/[...key] proxy — the R2 bucket has no public
 * r2.dev access and the Worker at podcasts.marklab.uk requires Basic
 * Auth that browsers won't carry in <audio src>. The proxy is itself
 * CF-Access-gated, so this keeps audio behind the same trust boundary
 * as the rest of dispatch.marklab.uk.
 */
export function EpisodeCard({ episode }: Props) {
  const audioUrl = audioUrlFor(episode.audio_key);
  const durationLabel = formatDuration(episode.duration_seconds);
  const ready = episode.status === "ready" && audioUrl;

  return (
    <article className="py-5 border-b border-hair grid grid-cols-[64px_1fr] gap-5">
      <div className="font-mono text-[34px] font-bold leading-none tabular-nums text-ink pt-1">
        {String(episode.episode_no).padStart(3, "0")}
      </div>

      <div>
        <h3 className="font-disp text-lg font-semibold leading-tight tracking-[-0.01em] text-ink">
          {episode.title}
        </h3>
        <div className="font-mono text-[10.5px] uppercase tracking-[0.18em] text-ink-mute mt-1.5 flex gap-3 flex-wrap items-center">
          <span>Week of {episode.week_start}</span>
          {durationLabel && (
            <>
              <span className="text-hair-strong">·</span>
              <span>{durationLabel}</span>
            </>
          )}
          <span className="text-hair-strong">·</span>
          <StatusTag status={episode.status} />
        </div>

        {ready ? (
          <audio
            controls
            preload="none"
            className="mt-3.5 w-full max-w-[520px] block"
            aria-label={`Play ${episode.title}`}
          >
            <source src={audioUrl} type="audio/mpeg" />
            Your browser doesn't support audio playback.
          </audio>
        ) : (
          <p className="mt-3 font-mono text-[10.5px] uppercase tracking-[0.18em] text-ink-mute italic">
            {episode.status === "failed"
              ? "Episode generation failed — see backend logs."
              : "Audio not yet available."}
          </p>
        )}
      </div>
    </article>
  );
}

function StatusTag({ status }: { status: string }) {
  const styles: Record<string, string> = {
    ready: "text-signal",
    composing: "text-ink-mute",
    awaiting_nblm: "text-ink-mute",
    downloading: "text-ink-mute",
    failed: "text-ink-mute line-through",
  };
  return (
    <span className={`font-semibold ${styles[status] ?? "text-ink-mute"}`}>
      {status.replace("_", " ")}
    </span>
  );
}

function formatDuration(seconds: number | null): string | null {
  if (!seconds || seconds <= 0) return null;
  const mins = Math.round(seconds / 60);
  return `${mins} min`;
}

function audioUrlFor(audioKey: string | null): string | null {
  if (!audioKey) return null;
  // The R2 key (e.g. "podcast/aether-focus/episode-001-2026-05-17.mp3")
  // is path-segment-encoded individually so the catch-all route receives
  // it cleanly; a flat encodeURIComponent would turn slashes into %2F.
  const encoded = audioKey.split("/").map(encodeURIComponent).join("/");
  return `/api/audio/${encoded}`;
}
