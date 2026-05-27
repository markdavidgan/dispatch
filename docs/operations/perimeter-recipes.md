# Perimeter Recipes

Dispatch has no app-layer authentication. The backend trusts its deployment
perimeter. Route prefixes are designed so any perimeter can apply policy:

- `/admin/*` and `/api/admin/*` — operator-only (must gate)
- `/`, `/briefings/*`, `/podcasts/*`, `/api/snapshot` — public reader paths
  (gate these too if you want a fully private instance)

All recipes below use placeholder hostnames (`example.com`, `dispatch.example.com`,
`api.example.com`). Substitute your own.

## Cloudflare Access

Run frontend and backend under a shared apex domain so a single Access
application policy gates both, and the auth cookie covers all subdomains.

1. Create a Cloudflare Access application for `*.example.com`.
2. Add an allowlist policy (email, identity provider, IP range, etc.).
3. Deploy the frontend to Vercel (or any static host) on `dispatch.example.com`.
4. Deploy the backend to a VPS / homelab box on `api.example.com`, also behind
   the same Access application.
5. Set `VITE_DISPATCH_API_URL=https://api.example.com` in the frontend build **only if** you need the podcast proxy fallback to reach the self-hosted backend directly. In normal operation the Vercel tier serves `/api/*` itself; the SPA's main API client uses same-origin `/api`.

**CORS bootstrap for split deployments**

Because the SPA and backend are on different origins, the backend must allow
the frontend origin in CORS. The easiest way is to set the env var at
backend boot time:

```bash
DISPATCH_CORS_ORIGINS=https://dispatch.example.com
```

(You can also set `web.allowed_origins` via the admin UI once you're in;
the env var is just there to avoid a chicken-and-egg problem on first
deployment.)

If you serve podcast episodes through the backend (local-filesystem storage
rather than R2/S3 presigned URLs), episode `<audio>` elements will also need
the Access cookie. The frontend already sends `credentials: "include"` on
API calls.

### Cloudflare Access — Public demo with gated admin routes

If you want the **reader-facing pages public** and only the **admin UI + admin
API** behind Cloudflare Access, create **two path-scoped Access applications**
on the same hostname:

| Application | Path | Policy |
|-------------|------|--------|
| Admin SPA | `dispatch-demo.example.com/admin*` | Require identity (email allowlist, OTP, or IdP) |
| Admin API | `dispatch-demo.example.com/api/admin*` | Same identity requirement |

Leave the root paths (`/`, `/briefings/*`, `/podcasts/*`, `/api/snapshot`,
etc.) uncovered — they pass through to the origin with no Access challenge.

**Why this works without code changes**

- The SPA (`/admin*`) and the backend (`/api/admin*`) live on the **same
  origin**, so the browser automatically sends the `CF_Authorization` cookie
  with every `fetch()` call. No `credentials: "include"` or CORS changes are
  needed.
- After the user authenticates through the Cloudflare Access login page, the
  cookie is valid for the entire domain. Navigating to `/admin/settings` or
  calling `/api/admin/settings` both carry the same session.

**Setup steps**

1. Ensure `dispatch-demo.example.com` is **orange-clouded** (proxied) in
   Cloudflare DNS.
2. In **Zero Trust → Access → Applications**, click *Add an application*.
3. Choose *Self-hosted*.
4. **Application 1 (Admin SPA):**
   - Application name: `dispatch-admin-spa`
   - Session duration: `24h` (or your preference)
   - Domain: `dispatch-demo.example.com`
   - Path: `/admin*`  
   - Identity providers: pick your IdP or *One-time PIN*.
   - Policy name: `admin-only`
   - Action: *Allow*
   - Include: *Emails* → add your email address(es).
5. **Application 2 (Admin API):**
   - Repeat the above but set Path to `/api/admin*`.
   - Policy: same `admin-only` allowlist.
6. Save both. Changes propagate in ~60 seconds.

**Hardening the origin**

Because the app is perimeter-trusting with no app-layer auth, anyone who
bypasses Cloudflare and hits the origin IP directly could reach `/api/admin/*`.
Lock down the origin server's firewall to **only Cloudflare IP ranges**:

- Cloudflare publishes its IP ranges at
  https://www.cloudflare.com/ips/ — allow only those on ports 80/443
  (and your SSH port from your own IP).
- If you run on a VPS, most providers have a cloud-firewall UI where you can
  paste these CIDR blocks.

## Tailscale Funnel

Expose the backend over the Tailscale mesh; only devices in your tailnet
can reach it.

```bash
tailscale funnel 10060
```

The frontend can sit on Tailscale too, or be served from the same machine
(all-in-one Docker compose pattern below).

## Caddy Basic Auth (all-in-one default)

The repo ships a `caddy/Caddyfile` with a commented `basicauth` block.

```bash
# Generate a bcrypt password hash
caddy hash-password

# Edit caddy/Caddyfile — uncomment the basicauth block and paste the hash
# Then start Caddy
caddy run --config caddy/Caddyfile
```

Both `/admin/*` and `/api/admin/*` must be gated together; the shipped
template does this in one matcher.

## Authelia

Use Authelia as forward-auth middleware in front of Caddy or Nginx.

Example Caddy snippet:

```caddyfile
@admin {
    path /admin/* /api/admin/*
}
forward_auth @admin authelia:9091 {
    uri /api/verify?rd=https://auth.example.com
    copy_headers Remote-User Remote-Groups Remote-Name Remote-Email
}
```

## Sanity check

Whichever perimeter you choose, verify these behaviors before going live:

1. An unauthenticated request to `/admin/projects` returns the perimeter's
   challenge (HTTP 302 to login, 401, etc.) — not a Dispatch page.
2. An unauthenticated request to `/api/admin/settings` returns the same
   challenge — the backend should never see the request.
3. An authenticated request to `/api/snapshot` succeeds.

If any of those leak, your perimeter rules are incomplete.
