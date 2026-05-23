"use client";

import { useState } from "react";

export default function RefreshButton() {
  const [pending, setPending] = useState(false);
  const refresh = async () => {
    setPending(true);
    try {
      await fetch("/api/refresh", { method: "POST" });
      window.location.reload();
    } finally {
      setPending(false);
    }
  };
  return (
    <button
      onClick={refresh}
      disabled={pending}
      className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-mute hover:text-signal px-3 py-2.5 disabled:opacity-50"
    >
      {pending ? "Re-filing…" : "Re-file ↻"}
    </button>
  );
}
