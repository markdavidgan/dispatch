/**
 * Resolve a stored audio reference into a browser-loadable URL.
 *
 * Both the frontend and backend orchestrators upload briefing audio to the
 * same deterministic R2 key: `dispatch/audio/{date}-{kind}.mp3`. The DB
 * `audio_url` field may contain:
 *   - a permanent public URL (production with R2_PUBLIC_BASE_URL set)
 *   - an expired presigned URL (frontend upload when R2_PUBLIC_BASE_URL
 *     is missing — expires after 7 days)
 *   - a `local://` reference (backend local-filesystem storage)
 *
 * To avoid serving expired presigned URLs, this helper always derives the
 * canonical URL from the deterministic key rather than trusting the stored
 * value directly.
 */
export function resolveAudioUrl(
  storedUrl: string | null | undefined,
  date: string,
  kind: "lead" | "addendum",
): string | null {
  if (!storedUrl) return null;

  const base = process.env.R2_PUBLIC_BASE_URL?.replace(/\/$/, "") || "";
  const backendUrl =
    process.env.BACKEND_URL?.replace(/\/$/, "") ||
    "https://dispatch-demo-api.marklab.uk";

  // local:// references always go through the backend proxy
  if (storedUrl.startsWith("local://")) {
    return `${backendUrl}/api/audio/dispatch/audio/${date}-${kind}.mp3`;
  }

  // Use deterministic public URL when available; otherwise fall back to the
  // backend proxy which serves fresh presigned URLs or local files.
  if (base) {
    return `${base}/dispatch/audio/${date}-${kind}.mp3`;
  }
  return `${backendUrl}/api/audio/dispatch/audio/${date}-${kind}.mp3`;
}
