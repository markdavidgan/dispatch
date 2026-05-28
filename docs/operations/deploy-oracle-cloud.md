# Deploy Dispatch to Oracle Cloud Free Tier

Oracle Cloud Infrastructure (OCI) offers an **Always Free** ARM VM with 4 OCPU and 24 GB RAM — enough to run the entire Dispatch stack (backend + frontend + SQLite + ffmpeg + TTS) with headroom to spare.

> **Why Oracle Cloud?** It's the only major cloud provider offering a perpetually free VM tier with enough RAM for audio processing. No sleep timeouts, no request limits, no credit expiry.

---

## What you need

- An Oracle Cloud account (requires credit card for verification, but the tier is $0)
- A domain name (optional — you can use the VM's public IP directly)
- `ssh` and basic terminal comfort

---

## Step 1 — Create the VM

1. Log in to the [OCI Console](https://cloud.oracle.com/).
2. **Compute → Instances → Create Instance**.
3. Name it `dispatch`.
4. Under **Image and Shape**:
   - **Image:** Canonical Ubuntu 24.04 (or Oracle Linux 9)
   - **Shape:** VM.Standard.A1.Flex (ARM)
   - **OCPUs:** 4
   - **Memory:** 24 GB
5. Under **Networking**:
   - Create a new VCN or use an existing one.
   - **Important:** Add an ingress rule to the security list for **TCP port 80 and 443** (and whatever port you choose for Dispatch, default 8080).
6. Under **Add SSH Keys**:
   - Generate a new key pair or upload your public key.
7. Click **Create**.

Wait ~2 minutes for the instance to reach **RUNNING** state. Note the **Public IP Address**.

---

## Step 2 — SSH and install Docker

```bash
ssh -i ~/.ssh/your-key ubuntu@<PUBLIC_IP>

# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker (official Docker repo recommended)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose plugin
docker compose version  # Should report v2.x
```

---

## Step 3 — Clone and configure

```bash
git clone https://github.com/<your-username>/dispatch.git
cd dispatch

# Copy example env
cp apps/backend/.env.example .env
```

Edit `.env` with at least:

```bash
DISPATCH_MASTER_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(32))">
DISPATCH_HTTP_PORT=80
```

Add your credentials:
- `GOOGLE_APPLICATION_CREDENTIALS` — mount your GCP service account JSON
- `GITHUB_TOKEN` — for GitHub ingest
- `ANTHROPIC_API_KEY` or `KIMI_OAUTH_JSON` — for AI synthesis
- `R2_PUBLIC_BASE_URL`, `R2_ACCOUNT_ID`, etc. — for Cloudflare R2 storage (optional; local filesystem works too)

If using **local filesystem storage** (simplest start):
```bash
# Nothing extra needed — SQLite and media files live in Docker volumes
```

If using **R2**:
```bash
export R2_PUBLIC_BASE_URL=https://your-account.r2.dev
export CLOUDFLARE_ACCOUNT_ID=...
export CLOUDFLARE_EMAIL=...
export CLOUDFLARE_GLOBAL_API_KEY=...
```

---

## Step 4 — Deploy

```bash
docker compose up -d
```

The stack comes up in ~30 seconds:
- **Frontend (Caddy)** on port 80
- **Backend (FastAPI)** on port 10060 (internal)
- **SQLite** in `dispatch-data` volume

Verify:
```bash
curl -fsS http://<PUBLIC_IP>/health
curl -fsS http://<PUBLIC_IP>/api/snapshot
```

---

## Step 5 — First-boot setup

Visit `http://<PUBLIC_IP>/setup` in a browser:

1. **Storage** — choose "Local filesystem" (or R2 if configured)
2. **AI Provider** — enter your API key
3. **TTS** — Google Cloud Chirp 3 HD (credentials already mounted)
4. **GitHub Token** — for repo monitoring
5. **First Project** — add a project to monitor

The wizard writes encrypted settings to SQLite. From then on, everything is configured via `/admin/settings`.

---

## Step 6 — Domain + SSL (optional but recommended)

If you have a domain, point an A record to the VM's public IP. Then update `caddy/Caddyfile`:

```caddy
your-domain.com {
    reverse_proxy /api/* dispatch-backend:10060
    reverse_proxy /health dispatch-backend:10060
    reverse_proxy /* dispatch-frontend:80
}
```

Caddy automatically provisions Let's Encrypt certificates. Rebuild:

```bash
docker compose down
docker compose up -d --build
```

---

## Step 7 — Backups

The backend runs an automatic nightly SQLite backup to your configured storage backend. You can also trigger one manually:

```bash
curl -fsS -X POST http://<PUBLIC_IP>/api/admin/system/backup-now
```

---

## Troubleshooting

**Container won't start — `DISPATCH_MASTER_KEY` missing:**
```bash
docker compose logs dispatch-backend
# Generate one and update .env
docker compose up -d
```

**SQLite "database is locked":**
The container uses WAL mode by default. If you see locks, ensure you're not running two backends against the same volume.

**Port 80 permission denied:**
On some systems, non-root processes can't bind port 80. Either:
- Use a higher port (`DISPATCH_HTTP_PORT=8080`) and reverse-proxy with Nginx/Caddy on the host
- Or grant the capability: `sudo setcap cap_net_bind_service=+ep $(which caddy)` inside the container

---

## Cost

$0. The Always Free ARM tier has no time limit and no usage cap within the allocated resources.
