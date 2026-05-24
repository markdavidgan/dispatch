# Perimeter Recipes

Dispatch has no app-layer authentication. The backend trusts its deployment
perimeter. Route prefixes are designed so any perimeter can apply policy:

- `/admin/*` and `/api/admin/*` — operator-only
- `/`, `/briefings/*`, `/podcasts/*`, `/api/snapshot` — public reader paths

## Cloudflare Access (author's pattern)

Both frontend and backend share an apex domain (`*.markdavidgan.com`).
One CF Access application policy gates the apex with the operator's email
allowlist. Cookie set at `.markdavidgan.com` covers all subdomains.

1. Create a Cloudflare Access application for `*.markdavidgan.com`
2. Add an allowlist policy with your email
3. Deploy frontend to Vercel on `dispatch.markdavidgan.com`
4. Deploy backend to VPS on `api.marklab.uk` (also behind CF Access)
5. Set `VITE_DISPATCH_API_URL=https://api.marklab.uk` in frontend build

## Tailscale Funnel

Expose the backend via Tailscale; only devices in your tailnet reach it.

```bash
tailscale funnel 10060
```

Frontend can also be on Tailscale or served from the same machine.

## Caddy Basic Auth (all-in-one default)

The repo ships a `caddy/Caddyfile` with a commented `basicauth` block.

```bash
# Generate password hash
caddy hash-password

# Edit caddy/Caddyfile — uncomment the basicauth block and paste the hash
# Then start Caddy
caddy run --config caddy/Caddyfile
```

Both `/admin/*` and `/api/admin/*` must be gated together.

## Authelia

Use Authelia as forward-auth middleware in front of Caddy or Nginx.

Example Caddy config:
```
@admin {
    path /admin/* /api/admin/*
}
forward_auth @admin authelia:9091 {
    uri /api/verify?rd=https://auth.example.com
    copy_headers Remote-User Remote-Groups Remote-Name Remote-Email
}
```
