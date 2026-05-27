import { useState, useRef, useCallback } from "react";

interface Props {
  leadUrl?: string | null;
  addendumUrl?: string | null;
}

function fmtTime(sec: number): string {
  if (!isFinite(sec) || sec < 0) return "0:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

export default function AudioPlayer({ leadUrl, addendumUrl }: Props) {
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [hoverPct, setHoverPct] = useState<number | null>(null);
  const [loadError, setLoadError] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const barRef = useRef<HTMLDivElement | null>(null);
  const src = addendumUrl || leadUrl;
  const hasAudio = Boolean(src);
  const canPlay = hasAudio && !loadError;

  const pct = duration > 0 ? (currentTime / duration) * 100 : 0;

  const seekTo = useCallback(
    (clientX: number) => {
      const bar = barRef.current;
      const audio = audioRef.current;
      if (!bar || !audio || !duration) return;
      const rect = bar.getBoundingClientRect();
      const fraction = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
      audio.currentTime = fraction * duration;
    },
    [duration]
  );

  const toggle = () => {
    const audio = audioRef.current;
    if (!audio || !canPlay) return;
    if (playing) audio.pause();
    else audio.play().catch(() => {});
  };

  const handleBarClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!canPlay) return;
    seekTo(e.clientX);
  };

  const handleBarMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!canPlay) return;
    const bar = barRef.current;
    if (!bar) return;
    const rect = bar.getBoundingClientRect();
    const fraction = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
    setHoverPct(fraction * 100);
  };

  const handleBarMouseLeave = () => {
    setHoverPct(null);
  };

  return (
    <div className={`flex items-center gap-4 w-full max-w-[520px] ${!canPlay ? "opacity-40" : ""}`}>
      {/* Play / Pause */}
      <button
        type="button"
        onClick={canPlay ? toggle : undefined}
        disabled={!canPlay}
        aria-label={playing ? "Pause" : "Play"}
        className={`shrink-0 inline-flex items-center justify-center w-9 h-9 border transition-colors ${
          playing
            ? "bg-signal border-signal text-paper"
            : canPlay
              ? "border-ink text-ink hover:bg-ink hover:text-paper cursor-pointer"
              : "border-ink text-ink cursor-not-allowed"
        }`}
      >
        {playing ? (
          <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor" aria-hidden>
            <rect x="0" y="0" width="3.5" height="10" />
            <rect x="6.5" y="0" width="3.5" height="10" />
          </svg>
        ) : (
          <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor" aria-hidden>
            <polygon points="0,0 10,5 0,10" />
          </svg>
        )}
      </button>

      {/* Scrubber */}
      <div
        ref={barRef}
        className={`group relative flex-1 h-6 flex items-center ${canPlay ? "cursor-pointer" : "cursor-default"}`}
        onClick={handleBarClick}
        onMouseMove={handleBarMouseMove}
        onMouseLeave={handleBarMouseLeave}
        role="slider"
        aria-label="Seek"
        aria-valuemin={0}
        aria-valuemax={duration ? Math.round(duration) : 0}
        aria-valuenow={currentTime ? Math.round(currentTime) : 0}
        aria-valuetext={`${fmtTime(currentTime)} of ${fmtTime(duration)}`}
        tabIndex={hasAudio ? 0 : -1}
        onKeyDown={(e) => {
          if (!canPlay) return;
          const audio = audioRef.current;
          if (!audio || !duration) return;
          if (e.key === "ArrowLeft") {
            e.preventDefault();
            audio.currentTime = Math.max(0, audio.currentTime - 5);
          } else if (e.key === "ArrowRight") {
            e.preventDefault();
            audio.currentTime = Math.min(duration, audio.currentTime + 5);
          } else if (e.key === "Home") {
            e.preventDefault();
            audio.currentTime = 0;
          } else if (e.key === "End") {
            e.preventDefault();
            audio.currentTime = duration;
          }
        }}
      >
        {/* Track */}
        <div className="w-full h-[3px] bg-hair rounded-full overflow-hidden">
          {/* Fill */}
          <div
            className="h-full bg-ink rounded-full transition-[width] duration-75"
            style={{ width: `${pct}%` }}
          />
        </div>

        {/* Thumb */}
        <div
          className="absolute top-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full bg-ink opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none"
          style={{ left: `calc(${pct}% - 5px)` }}
        />

        {/* Hover preview time */}
        {hoverPct !== null && canPlay && (
          <div
            className="absolute -top-5 pointer-events-none font-mono text-[10px] text-ink-mute tabular-nums"
            style={{ left: `calc(${hoverPct}% - 12px)` }}
          >
            {fmtTime((hoverPct / 100) * duration)}
          </div>
        )}
      </div>

      {/* Time */}
      <span className="shrink-0 font-mono text-[11px] tabular-nums text-ink-mute tracking-[0.04em] w-[80px] text-right">
        {canPlay ? fmtTime(currentTime) : "--:--"}{" "}
        <span className="text-hair-strong">/</span>{" "}
        {canPlay ? fmtTime(duration) : "--:--"}
      </span>

      {hasAudio && (
        <audio
          ref={audioRef}
          src={src || undefined}
          preload="metadata"
          onLoadedMetadata={() => {
            if (audioRef.current) {
              setDuration(audioRef.current.duration || 0);
              setLoadError(false);
            }
          }}
          onError={() => setLoadError(true)}
          onTimeUpdate={() => {
            if (audioRef.current) setCurrentTime(audioRef.current.currentTime || 0);
          }}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onEnded={() => setPlaying(false)}
        />
      )}
    </div>
  );
}
