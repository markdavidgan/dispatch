// marklab-dev-podcasts
// Basic-Auth gated reverse proxy in front of the marklab-media R2 bucket.
// Serves both Phase 1 audio (/dispatch/audio/...) and Phase 2 podcasts
// (/<project-slug>{.xml,/episode-...}).

interface Env {
  MEDIA: R2Bucket;
  AUTH_USERNAME: string;
  AUTH_PASSWORD: string;
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url);

    // Basic Auth gate
    const auth = req.headers.get("Authorization") ?? "";
    if (!auth.startsWith("Basic ")) {
      return unauthorized();
    }
    const [user, pass] = atob(auth.slice(6)).split(":", 2);
    if (user !== env.AUTH_USERNAME || pass !== env.AUTH_PASSWORD) {
      return unauthorized();
    }

    // Map path → R2 key.
    //   /dispatch/...               → marklab-media/dispatch/...
    //   /<slug>.xml or /<slug>/...  → marklab-media/podcast/<slug>...
    const path = url.pathname.replace(/^\//, "");
    if (!path) return new Response("Not found", { status: 404 });
    const key = path.startsWith("dispatch/") ? path : `podcast/${path}`;

    // Range support for MP3 streaming
    const range = req.headers.get("Range");
    let r2opts: R2GetOptions | undefined;
    if (range) {
      const m = range.match(/bytes=(\d+)-(\d*)/);
      if (m) {
        const offset = parseInt(m[1], 10);
        const length = m[2] ? parseInt(m[2], 10) - offset + 1 : undefined;
        r2opts = { range: length !== undefined ? { offset, length } : { offset } };
      }
    }

    const obj = await env.MEDIA.get(key, r2opts);
    if (!obj) return new Response("Not found", { status: 404 });

    const headers = new Headers();
    obj.writeHttpMetadata(headers);
    headers.set("etag", obj.httpEtag);
    if (key.endsWith(".xml")) headers.set("content-type", "application/rss+xml");
    if (key.endsWith(".mp3")) headers.set("accept-ranges", "bytes");

    const anyObj = obj as unknown as { range?: { offset: number; length: number }; size: number };
    if (anyObj.range) {
      headers.set(
        "content-range",
        `bytes ${anyObj.range.offset}-${anyObj.range.offset + anyObj.range.length - 1}/${anyObj.size}`,
      );
      return new Response(obj.body, { status: 206, headers });
    }
    return new Response(obj.body, { headers });
  },
};

function unauthorized(): Response {
  return new Response("Unauthorized", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="marklab podcasts"' },
  });
}
