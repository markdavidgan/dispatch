import { audioUrl } from "@/lib/api";

const STATUS_MESSAGE: Record<string, string> = {
  failed: "Episode generation failed — see backend logs.",
  failed_auth: "NotebookLM authentication failed — check session in admin / settings.",
  failed_transient: "Generation failed (transient) — will retry on next schedule.",
  skipped: "Skipped — NotebookLM session not configured.",
};

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

interface Props {
  episode: Episode;
}

export function EpisodeCard({ episode }: Props) {
  const url = episode.audio_key ? audioUrl(episode.audio_key) : null;
  const durationLabel = formatDuration(episode.duration_seconds);
  const ready = episode.status === "ready" && url;

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
            crossOrigin="use-credentials"
            className="mt-3.5 w-full max-w-[520px] block"
            aria-label={`Play ${episode.title}`}
          >
            <source src={url} type="audio/mpeg" />
            Your browser doesn't support audio playback.
          </audio>
        ) : (
          <p className="mt-3 font-mono text-[10.5px] uppercase tracking-[0.18em] text-ink-mute italic">
            {STATUS_MESSAGE[episode.status] ?? "Audio not yet available."}
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
    failed_auth: "text-ink-mute line-through",
    failed_transient: "text-ink-mute line-through",
    skipped: "text-ink-mute line-through",
  };
  return (
    <span className={`font-semibold ${styles[status] ?? "text-ink-mute"}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

function formatDuration(seconds: number | null): string | null {
  if (!seconds || seconds <= 0) return null;
  const mins = Math.round(seconds / 60);
  return `${mins} min`;
}
