import { useState } from "react";
import { generateBriefing } from "@/lib/api";

interface Props {
  onSuccess?: () => void;
  label?: string;
  variant?: "inline" | "button";
}

export default function RefreshButton({ onSuccess, label, variant = "inline" }: Props) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  const refresh = async () => {
    setPending(true);
    setError("");
    try {
      const result = await generateBriefing();
      if (result.generated) {
        if (onSuccess) onSuccess();
        else window.location.reload();
      } else if (result.reason) {
        setError(`Skipped: ${result.reason}`);
      }
    } catch (e: any) {
      setError(e.message || "Generation failed.");
    } finally {
      setPending(false);
    }
  };

  if (variant === "button") {
    return (
      <div>
        <button
          onClick={refresh}
          disabled={pending}
          className="font-mono text-[11px] uppercase tracking-[0.14em] font-semibold px-5 py-2.5 bg-signal text-paper hover:bg-ink transition-colors disabled:opacity-50"
        >
          {pending ? "Generating…" : (label || "Generate Briefing")}
        </button>
        {error && (
          <div className="mt-3 px-4 py-3 border border-signal text-signal font-mono text-[11px]">
            {error}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={refresh}
        disabled={pending}
        className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-mute hover:text-signal px-3 py-2.5 disabled:opacity-50"
      >
        {pending ? "Re-filing…" : (label || "Re-file ↻")}
      </button>
      {error && (
        <span className="font-mono text-[11px] text-signal">{error}</span>
      )}
    </div>
  );
}
