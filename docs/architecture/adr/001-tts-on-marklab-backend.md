# ADR 001: Keep TTS on the Self-Hosted Backend

**Status:** Accepted  
**Date:** 2026-05-27  
**Deciders:** markdavidgan  

## Context

During the Vercel serverless migration (plan: `2026-05-26-briefings-vercel-serverless.md`), the assumption was that TTS would move to Vercel alongside ingest, synthesis, and publish. The plan listed Kokoro via Hugging Face Inference API or ElevenLabs as replacements for Google Cloud Chirp 3 HD + ffmpeg.

After attempting to wire Kokoro TTS into the Vercel pipeline, we discovered:

1. **`api-inference.huggingface.co` is decommissioned.** The domain no longer resolves. HF migrated their serverless Inference API to `router.huggingface.co`, which is an LLM-routing gateway that does not serve TTS models like Kokoro.
2. **Self-hosted Kokoro in Vercel serverless is impractical.** `kokoro-js` (ONNX Runtime in Node.js) requires `espeak-ng` and a WASM phonemizer that fails in the Vercel Linux environment. The package + model download exceeds reasonable serverless bundle and cold-start budgets.
3. **The marklab backend already had working Google Cloud TTS.** It was running, fully configured with `GOOGLE_APPLICATION_CREDENTIALS`, and had already generated Issue #1 audio before the migration started.

## Decision

**Keep TTS generation on the self-hosted marklab backend.** The Vercel frontend delegates audio generation to the backend via `POST /api/tts/generate` instead of running TTS inside Vercel functions.

## Consequences

### Positive

- **No new TTS provider needed.** Google Cloud Chirp 3 HD (Ava/Leda voice) continues to work. No API keys to rotate, no new bills, no free-tier limits to watch.
- **No ffmpeg on Vercel.** The backend already handles chunking, Google TTS per-chunk, ffmpeg concat, and loudnorm normalization. The frontend receives a finished MP3.
- **Faster Vercel builds.** No `kokoro-js` (~30 MB) or `@huggingface/transformers` (~136 MB) in the function bundle.
- **Backend gains a new API surface.** `POST /api/tts/generate` is a clean, reusable endpoint that any caller (Vercel cron, admin UI, future integrations) can use.

### Negative

- **Network dependency.** Vercel → marklab is an extra HTTP hop for every audio generation. On a daily cron this is negligible; on-demand addendums add ~2 s latency.
- **Backend must stay up for audio.** If the marklab box is down, new briefings synthesize but have no audio. The frontend falls back gracefully (disabled player state), and a retry cron (`/api/cron/audio`) catches up once the backend returns.
- **Two sources of truth for audio files.** The frontend's Turso DB stores `audio_url` when `runAudio()` succeeds. The backend's local SQLite also stores `audio_url` when its own `run_audio()` succeeds. The two are not synced. We mitigate this by having the frontend fall back to the backend's deterministic audio URL (`/api/audio/dispatch/audio/{date}-{kind}.mp3`) when its own DB has no `audio_url`.

## Alternatives Considered

| Option | Why Rejected |
|---|---|
| **Kokoro via HuggingFace Inference API** | `api-inference.huggingface.co` is decommissioned (DNS failure, confirmed from Vercel and local). |
| **Kokoro via `kokoro-js` in Vercel** | WASM phonemizer fails in serverless; 166 MB bundle; model download on every cold start. |
| **ElevenLabs** | Requires a new API key + paid plan for production volume. No compelling quality advantage over Google Chirp 3 HD we already have. |
| **OpenAI TTS** | Requires a new API key; $15/M chars adds ~$0.015/day. Simpler API but no cost savings over existing free Google Cloud credits. |
| **Move backend entirely to Vercel** | Podcast pipeline (NotebookLM 4-hour polling, ffmpeg) is fundamentally incompatible with Vercel serverless. Backend must stay somewhere. |

## Related

- Plan: `docs/plans/2026-05-26-briefings-vercel-serverless.md`
- Backend TTS endpoint: `apps/backend/dispatch/api/tts.py`
- Frontend TTS client: `apps/frontend/api/_lib/tts.ts`
- Frontend fallback logic: `apps/frontend/api/_lib/snapshot.ts`, `apps/frontend/api/briefing.ts`
