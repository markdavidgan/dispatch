/**
 * Server-side audio proxy: dispatch.marklab.uk/api/audio/<r2-key>
 *
 * The Cloudflare R2 bucket isn't publicly readable (r2.dev returns 500),
 * and the Worker at podcasts.marklab.uk requires Basic Auth that modern
 * browsers can't inject into <audio src=...>. So we proxy through the
 * frontend, which is itself CF-Access-gated — same trust boundary as the
 * rest of dispatch.marklab.uk, no new exposure.
 *
 * Supports HTTP Range requests (HTML5 <audio> uses them for seeking).
 */
import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function r2ObjectUrl(key: string): string {
  const account = process.env.CLOUDFLARE_ACCOUNT_ID;
  const bucket = process.env.R2_BUCKET_NAME ?? "marklab-media";
  if (!account) throw new Error("CLOUDFLARE_ACCOUNT_ID not configured");
  return `https://api.cloudflare.com/client/v4/accounts/${account}/r2/buckets/${bucket}/objects/${key}`;
}

function r2Headers(): HeadersInit {
  const email = process.env.CLOUDFLARE_EMAIL;
  const key = process.env.CLOUDFLARE_GLOBAL_API_KEY;
  if (!email || !key) throw new Error("Cloudflare credentials not configured");
  return { "X-Auth-Email": email, "X-Auth-Key": key };
}

function contentTypeFromKey(key: string): string {
  if (key.endsWith(".mp3")) return "audio/mpeg";
  if (key.endsWith(".m4a")) return "audio/mp4";
  if (key.endsWith(".wav")) return "audio/wav";
  if (key.endsWith(".ogg")) return "audio/ogg";
  return "application/octet-stream";
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ key: string[] }> }
) {
  const { key: keyParts } = await params;
  if (!keyParts || keyParts.length === 0) {
    return new Response("missing key", { status: 400 });
  }
  const key = keyParts.map(decodeURIComponent).join("/");

  // Only allow keys under known prefixes so the proxy can't be abused
  // to enumerate the bucket. Add prefixes here as new audio kinds land.
  const allowed = ["dispatch/audio/", "podcast/"];
  if (!allowed.some((p) => key.startsWith(p))) {
    return new Response("forbidden", { status: 403 });
  }

  const range = request.headers.get("range");
  const upstreamHeaders: HeadersInit = { ...r2Headers() };
  if (range) {
    (upstreamHeaders as Record<string, string>).Range = range;
  }

  let upstream: Response;
  try {
    upstream = await fetch(r2ObjectUrl(key), {
      headers: upstreamHeaders,
      cache: "no-store",
    });
  } catch (err) {
    return new Response(
      `R2 fetch failed: ${err instanceof Error ? err.message : String(err)}`,
      { status: 502 },
    );
  }

  if (!upstream.ok && upstream.status !== 206) {
    return new Response(upstream.statusText || "upstream error", {
      status: upstream.status,
    });
  }

  // Pass through the body + the headers that matter for streaming audio.
  const passthrough = new Headers();
  passthrough.set("Content-Type", contentTypeFromKey(key));
  const len = upstream.headers.get("content-length");
  if (len) passthrough.set("Content-Length", len);
  const rangeHeader = upstream.headers.get("content-range");
  if (rangeHeader) passthrough.set("Content-Range", rangeHeader);
  const acceptRanges = upstream.headers.get("accept-ranges");
  passthrough.set("Accept-Ranges", acceptRanges ?? "bytes");
  // Short cache so a re-load isn't a fresh proxy hit, but invalidations
  // (new episode at same key — unlikely; keys carry the date) are tolerable.
  passthrough.set("Cache-Control", "private, max-age=3600");

  return new Response(upstream.body, {
    status: upstream.status,
    headers: passthrough,
  });
}

export async function HEAD(
  request: NextRequest,
  ctx: { params: Promise<{ key: string[] }> }
) {
  // Some podcast clients HEAD before GET; mirror GET's headers without
  // the body. Reuses the same allowlist guard via the GET handler.
  const r = await GET(request, ctx);
  return new Response(null, { status: r.status, headers: r.headers });
}
