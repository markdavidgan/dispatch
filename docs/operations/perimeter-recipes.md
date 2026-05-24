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
5. Set `VITE_DISPATCH_API_URL=https://api.example.com` in the frontend build.

The Access cookie issued at the apex covers both subdomains, so the SPA can
`fetch(backend, { credentials: "include" })` and Cloudflare transparently
authenticates the call.

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
