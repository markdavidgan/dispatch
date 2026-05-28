# Deploy Dispatch to Fly.io

Fly.io is a developer-friendly platform for running Docker containers close to users. Their free tier is suitable for lightweight workloads, though Dispatch's audio processing (ffmpeg + TTS) pushes against the memory limit.

> **When to choose Fly.io:** You want a simpler setup than Oracle Cloud and don't mind paying ~$2/mo for a 512 MB VM if the free 256 MB tier proves too tight.

---

## What you need

- A [Fly.io](https://fly.io) account
- `flyctl` installed locally
- A credit card (Fly.io requires one even for the free tier)

---

## Step 1 — Initialize the app

```bash
cd dispatch/apps/backend
flyctl apps create dispatch-backend
```

This creates the app without deploying yet.

---

## Step 2 — Create a persistent volume

SQLite needs a persistent volume:

```bash
flyctl volumes create dispatch_data --region sin --size 3
```

> Free tier includes 3 GB of persistent volume. Adjust `--region` to one close to you.

---

## Step 3 — Set secrets

```bash
flyctl secrets set DISPATCH_MASTER_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
flyctl secrets set DISPATCH_TZ="Asia/Manila"
flyctl secrets set ANTHROPIC_API_KEY="..."
flyctl secrets set GITHUB_TOKEN="..."
flyctl secrets set GOOGLE_APPLICATION_CREDENTIALS="/etc/dispatch/gcp-sa.json"
```

For R2 storage (optional):
```bash
flyctl secrets set R2_PUBLIC_BASE_URL="..."
flyctl secrets set CLOUDFLARE_ACCOUNT_ID="..."
flyctl secrets set CLOUDFLARE_EMAIL="..."
flyctl secrets set CLOUDFLARE_GLOBAL_API_KEY="..."
```

---

## Step 4 — Deploy

Fly.io uses a `fly.toml` file for configuration. Create `apps/backend/fly.toml`:

```toml
app = 'dispatch-backend'
primary_region = 'sin'

[build]
  dockerfile = 'Dockerfile'

[env]
  HOST = '0.0.0.0'
  PORT = '10060'
  DB_PATH = '/data/dispatch.db'

[[mounts]]
  source = 'dispatch_data'
  destination = '/data'

[http_service]
  internal_port = 10060
  force_https = true
  auto_stop_machines = 'off'
  auto_start_machines = true
  min_machines_running = 1
  processes = ['app']

[[vm]]
  memory = '512mb'
  cpu_kind = 'shared'
  cpus = 1
```

> **Memory note:** The free tier provides 256 MB VMs. Dispatch backend alone boots in ~180 MB, but TTS + ffmpeg spikes above 256 MB. If you hit OOMs during audio generation, upgrade to the 512 MB VM (~$1.94/mo).

Deploy:
```bash
flyctl deploy
```

---

## Step 5 — Verify

```bash
flyctl status
flyctl logs

curl -fsS https://dispatch-backend.fly.dev/health
curl -fsS https://dispatch-backend.fly.dev/api/snapshot
```

---

## Step 6 — Frontend

You have two options for the frontend:

### A) Static demo on Vercel (recommended)
Build the static demo and deploy to Vercel:
```bash
cd ../frontend
npm run build:demo
vercel --prod --local-config vercel.demo.json
```
Point the demo's `DEMO_API_BASE` at your Fly.io backend when generating data.

### B) Fly.io frontend (all-in-one)
Deploy the Caddy frontend on Fly.io too, or run it locally behind Tailscale.

---

## Limitations vs Oracle Cloud

| Concern | Fly.io | Oracle Cloud |
|---------|--------|--------------|
| RAM free tier | 256 MB | 24 GB |
| Persistent storage | 3 GB | 200 GB |
| Sleep / idle | Never (if `min_machines_running = 1`) | Never |
| Cost at free limit | ~$2/mo for 512 MB | $0 |
| Setup complexity | Low | Medium |

**Verdict:** Use Fly.io if you value simplicity and don't mind a small monthly fee. Use Oracle Cloud if you want a genuinely free, powerful server.
