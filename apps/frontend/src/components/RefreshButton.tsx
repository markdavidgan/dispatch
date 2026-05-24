import { useState } from "react";
import { refreshBriefing } from "@/lib/api";

export default function RefreshButton() {
  const [pending, setPending] = useState(false);
  const refresh = async () => {
    setPending(true);
    try {
      await refreshBriefing();
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
