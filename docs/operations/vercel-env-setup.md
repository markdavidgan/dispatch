# Vercel Environment Setup Guide

This guide walks through creating all API keys and credentials needed to deploy the Dispatch briefings pipeline to Vercel.

## ✅ Already Done

| Item | Status |
|------|--------|
| R2 bucket `dispatch-media` created (APAC region) | ✅ |
| `DISPATCH_MASTER_KEY` (from Doppler dispatch/prd) | ✅ |
| `GITHUB_TOKEN` (from Doppler dispatch/prd) | ✅ |
| `R2_ACCOUNT_ID` = `7f5bbe163c03ce3b41590ff227ff6842` | ✅ |
| `R2_PUBLIC_BASE_URL` = `https://7f5bbe163c03ce3b41590ff227ff6842.r2.dev` | ✅ |

## ⏳ You Must Create (Manual Steps)

### 1. R2 S3-Compatible API Token

The Vercel serverless code uses the S3-compatible API to upload audio to R2. The Cloudflare Global API Key cannot be used for S3 access.

**Steps:**
1. Go to [Cloudflare Dashboard → R2 → Manage R2 API Tokens](https://dash.cloudflare.com/?to=/:account/r2/api-tokens)
2. Click **Create API Token**
3. Set:
   - **Name**: `dispatch-vercel`
   - **Permissions**: `Object Read & Write`
   - **Bucket**: `dispatch-media` only
4. Copy the **Access Key ID** and **Secret Access Key**
5. Save to Doppler dispatch/prd:
   ```
   R2_ACCESS_KEY_ID=<access-key-id>
   R2_SECRET_ACCESS_KEY=<secret-access-key>
   R2_BUCKET=dispatch-media
   ```

> **Note:** R2 buckets are private by default. Audio files will be served via presigned URLs (already supported in the code). If you want public direct URLs, enable public access for the bucket in the dashboard or add a custom domain.

---

### 2. Turso Database

Turso provides serverless SQLite over HTTP — perfect for Vercel's stateless functions.

**Steps:**
1. Install Turso CLI: `brew install tursodatabase/tap/turso` (or [other methods](https://docs.turso.dev/cli/introduction))
2. Login: `turso auth login`
3. Create database:
   ```bash
   turso db create dispatch --group <your-group> --location sin
   ```
4. Get the connection URL:
   ```bash
   turso db show dispatch --url
   ```
   Example output: `libsql://dispatch-<user>.turso.io`
5. Create an auth token:
   ```bash
   turso db tokens create dispatch
   ```
6. Save to Doppler dispatch/prd:
   ```
   TURSO_DATABASE_URL=libsql://dispatch-<user>.turso.io
   TURSO_AUTH_TOKEN=<token>
   ```

> **Note:** After creating the DB, run the schema migration. The schema is in `apps/backend/dispatch/db/schema.sql` (or create a Turso-specific migration). You can apply it with:
> ```bash
> turso db shell dispatch < apps/backend/dispatch/db/schema.sql
> ```

---

### 3. Gemini API Key (Free)

Primary LLM for briefings synthesis.

**Steps:**
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click **Create API Key**
3. Select a Google Cloud project (or create one)
4. Copy the key
5. Save to Doppler dispatch/prd:
   ```
   GEMINI_API_KEY=<key>
   GEMINI_MODEL=gemini-2.5-flash
   ```

> **Free tier limits:** 5 RPM, 100 RPD, 1M input tokens/day. More than enough for a daily briefing.

---

### 4. Groq API Key (Free — Fallback)

Fallback LLM when Gemini hits rate limits or is unavailable.

**Steps:**
1. Go to [Groq Console](https://console.groq.com/keys)
2. Click **Create API Key**
3. Copy the key
4. Save to Doppler dispatch/prd:
   ```
   GROQ_API_KEY=<key>
   GROQ_MODEL=llama-3.3-70b-versatile
   ```

> **Free tier limits:** 14,400 requests/day, 30 RPM.

---

### 5. Hugging Face API Token (Free)

Required for Kokoro TTS via the Hugging Face Inference API.

**Steps:**
1. Go to [Hugging Face Settings → Access Tokens](https://huggingface.co/settings/tokens)
2. Click **New Token**
3. Set:
   - **Name**: `dispatch-tts`
   - **Role**: `read`
4. Copy the token
5. Save to Doppler dispatch/prd:
   ```
   HF_API_TOKEN=<token>
   ```

> **Note:** The Inference API is free with rate limits. For production, consider self-hosting Kokoro or using a paid inference endpoint.

---

## 📋 Full Doppler Config (dispatch/prd)

After completing all steps, your Doppler `dispatch/prd` config should contain:

```
# Auth
DISPATCH_MASTER_KEY=<existing>

# Database
TURSO_DATABASE_URL=libsql://dispatch-<user>.turso.io
TURSO_AUTH_TOKEN=<create via turso CLI>

# LLM
GEMINI_API_KEY=<create at aistudio.google.com>
GROQ_API_KEY=<create at console.groq.com>

# TTS (delegated to backend — no HF token needed)
BACKEND_URL=https://dispatch-demo-api.marklab.uk

# Storage
R2_ACCOUNT_ID=7f5bbe163c03ce3b41590ff227ff6842
R2_ACCESS_KEY_ID=<create in Cloudflare dashboard>
R2_SECRET_ACCESS_KEY=<create in Cloudflare dashboard>
R2_BUCKET=dispatch-media
R2_PUBLIC_BASE_URL=https://7f5bbe163c03ce3b41590ff227ff6842.r2.dev

# Ingest
GITHUB_TOKEN=<existing>

# Podcast proxy (self-hosted backend)
PODCAST_BACKEND_URL=<your self-hosted URL>
```

## 🚀 Deploy to Vercel

Once all secrets are in Doppler:

```bash
cd apps/frontend
# Link to Vercel project
vercel link

# Pull secrets from Doppler and deploy
# Option 1: Manual env vars
vercel --prod

# Option 2: Doppler integration (recommended)
# Connect Doppler to Vercel in the Doppler dashboard
# https://docs.doppler.com/docs/vercel
```

## 🧪 Test Locally

```bash
cd apps/frontend
# Pull secrets from Doppler
doppler secrets download --project dispatch --config prd --format env --no-file > .env

# Run dev server
npm run dev
```
