"use client";

import { useState, useRef } from "react";

interface Props {
  leadUrl?: string | null;
  addendumUrl?: string | null;
  durationLabel?: string;   // e.g. "0:47"
}

export default function AudioPlayer({ leadUrl, addendumUrl, durationLabel = "" }: Props) {
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const src = addendumUrl || leadUrl;
  if (!src) return null;

  const toggle = () => {
    if (!audioRef.current) return;
    if (playing) audioRef.current.pause();
    else audioRef.current.play();
    setPlaying(!playing);
  };

  // <audio> sits as a sibling of <button>, not a child. HTML's button
  // content model forbids interactive descendants; nesting <audio> there
  // is invalid and causes some screen readers to expose the audio element
  // as a separate focusable item.
  return (
    <span className="inline-flex items-center">
      <button
        type="button"
        onClick={toggle}
        aria-label={playing ? "Pause briefing audio" : "Play briefing audio"}
        aria-pressed={playing}
        className={`inline-flex items-center gap-2.5 font-mono text-[11px] uppercase tracking-[0.18em] px-4 py-2.5 font-semibold border transition-colors ${
          playing
            ? "bg-signal border-signal text-paper"
            : "border-ink text-ink hover:bg-ink hover:text-paper"
        }`}
      >
        <span
          className={`w-2 h-2.5 bg-current ${playing ? "animate-pulse" : ""}`}
          style={{ clipPath: "polygon(0 0, 100% 50%, 0 100%)" }}
          aria-hidden
        />
        <span>TRANSMIT{durationLabel ? ` ${durationLabel}` : ""}</span>
      </button>
      <audio ref={audioRef} src={src} onEnded={() => setPlaying(false)} preload="none" />
    </span>
  );
}
