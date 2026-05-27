# Data Flow

Dispatch's job is to turn upstream development activity into a daily editorial
brief with audio, plus weekly podcast episodes. This document traces what
happens between a `git push` upstream and a reader opening the briefing page.

The pipeline is the same in both deployment modes; only the scheduler and
database differ:

- **All-in-One Docker:** APScheduler in-process + local SQLite
- **Hybrid (Vercel):** Vercel Cron Jobs + Turso (serverless SQLite over HTTP)

---

## End-to-end pipeline

```mermaid
flowchart LR
    subgraph upstream["Upstream"]
        gh[("GitHub repos")]
        git[("Local git clones")]
    end

    subgraph ingest["Ingest"]
        ig["ingest_github<br/>(every 30 min)"]
        igit["ingest_git<br/>(every 15 min)"]
    end

    events[("events table<br/>deduped by external_id")]

    subgraph synth["Synthesis"]
        sl["synthesis_lead<br/>(daily ~01:00)"]
        sd["synthesis_from_the_desk<br/>(weekly Sun ~23:00)"]
        sr["/api/brief/refresh<br/>(on demand)"]
    end

    filings[("filings table<br/>lead / addendum / desk")]

    subgraph audio["Audio generation"]
        tts_api["POST /api/tts/generate"]
        chunk["chunk text<br/>at sentence boundaries"]
        gtts["Google Chirp 3 HD<br/>(per chunk)"]
        ffmpeg["ffmpeg<br/>loudnorm + concat"]
    end

    mp3(("brief.mp3"))

    subgraph publish["Publish"]
        snap["build snapshot JSON"]
        store["upload to storage backend"]
        archive[("snapshot-archive/<br/>YYYY-MM-DD.json")]
    end

    subgraph podcast["Weekly podcast (per project)"]
        nlm["NotebookLM<br/>episode composition"]
        rss["RSS feed generation"]
    end

    gh --> ig --> events
    git --> igit --> events
    events --> sl --> filings
    events --> sd --> filings
    events --> sr --> filings
    filings --> tts_api --> chunk --> gtts --> ffmpeg --> mp3
    filings --> snap --> store --> archive
    mp3 --> store
    events --> nlm --> rss --> store
```

---

## Daily cycle

Default cadence in UTC; adjust per-instance under `/admin/schedules`.

```mermaid
sequenceDiagram
    autonumber
    participant Sched as Scheduler<br/>(APScheduler or Vercel Cron)
    participant Orch as orchestrator
    participant GH as GitHub REST
    participant DB as Database<br/>(SQLite or Turso)
    participant AI as AI provider
    participant TTS as TTS backend
    participant ST as Storage backend

    Note over Sched: every 30 min
    Sched->>Orch: ingest_github()
    Orch->>DB: load per-project cursors
    Orch->>GH: list events since cursor
    GH-->>Orch: PRs · issues · releases
    Orch->>DB: insert events (dedup by external_id)
    Orch->>DB: update cursor

    Note over Sched: daily ~01:00 UTC
    Sched->>Orch: synthesis_lead()
    Orch->>DB: select events from yesterday
    Orch->>AI: compose lead brief (JSON schema)
    AI-->>Orch: { headline, body, project_lines }
    Orch->>DB: insert filing (kind='lead')

    Orch->>TTS: POST /api/tts/generate
    TTS-->>Orch: MP3 bytes
    Orch->>ST: upload brief.mp3
    Orch->>ST: upload snapshot.json
    Orch->>DB: write run record
```

### On-demand addendum

Operators (or the SPA's "refresh" button) can trigger a same-day addendum
through `POST /api/brief/refresh`. The handler runs a compressed version of the
same pipeline with a 25-second timeout — synthesize, narrate, publish — and
attaches the result as an addendum filing to the day's brief.

---

## Weekly cycle

```mermaid
flowchart TB
    sun["Sunday ~23:00<br/>synthesis_from_the_desk"] --> desk["compose editor's memo"]
    desk --> filing["filings row<br/>(kind='desk')"]

    weekly_pod["Per-project weekly cron<br/>(podcast_intake job)"] --> nlm["NotebookLM<br/>episode composition"]
    nlm --> episode["episodes row"]
    episode --> rss["regenerate RSS feed"]
    rss --> upload["upload feed + audio<br/>to storage backend"]
```

Weekly outputs:

- **From the desk** — a longer editorial memo summarizing the week's themes.
  Joins the next day's brief as a separate section.
- **Per-project podcast episode** — NotebookLM composes a conversational
  audio episode from the week's briefings touching that project. The RSS feed
  for the project is regenerated and re-uploaded.

---

## Reader read-path

Static SPA, hydrated from JSON snapshots written by the publish step:

```mermaid
sequenceDiagram
    autonumber
    participant Reader
    participant Edge as Perimeter + Gateway
    participant SPA as Vite SPA
    participant API as API tier<br/>(FastAPI or Vercel Function)
    participant ST as Storage backend
    participant DB as Database

    Reader->>Edge: GET /
    Edge->>SPA: index.html + bundle
    SPA->>API: GET /api/snapshot
    API->>ST: fetch current snapshot.json
    ST-->>API: snapshot bytes
    API-->>SPA: snapshot JSON
    SPA->>SPA: render hero, projects, ticker

    Reader->>SPA: click briefing date
    SPA->>API: GET /api/briefings/{date}
    API->>DB: select filing
    API->>ST: fetch snapshot-archive/{date}.json (for recent_events)
    API-->>SPA: briefing payload
    SPA->>API: GET /api/audio/{key}
    API->>ST: presign URL (R2 / S3) or stream (local)
    API-->>SPA: 302 to MP3 or audio bytes
```

The snapshot pattern keeps the read path independent of the synthesis path:
publishes are atomic file uploads, and the SPA only ever reads the current
snapshot plus any archived briefings the reader navigates to.

---

## Audio fallback chain

When a filing has no `audio_url` in the database (e.g., TTS failed or the
backend was down), the frontend falls back in this order:

1. **`audio_url` from database** — the canonical URL written by the audio step.
2. **Backend deterministic URL** — `https://<backend-host>/api/audio/dispatch/audio/{date}-lead.mp3`. The backend may have generated audio independently.
3. **Storage deterministic URL** — `{STORAGE_PUBLIC_BASE_URL}/dispatch/audio/{date}-lead.mp3`. Used when the frontend successfully uploaded to storage but failed to write the DB row.

The `<audio>` element handles 404s gracefully, so a missing fallback is a silent
no-op rather than a broken UI.

---

## State machines

### Briefing filings

```mermaid
stateDiagram-v2
    [*] --> draft : synthesis writes filing
    draft --> narrated : TTS chunks + concat succeed
    narrated --> published : snapshot + audio uploaded
    draft --> failed : synthesis or schema validation error
    narrated --> failed : TTS or ffmpeg error
    published --> [*]
    failed --> [*]
```

Failures are recorded in the `runs` table with the error message, visible in
the admin Runs page.

### Podcast episodes

```mermaid
stateDiagram-v2
    [*] --> pending : podcast_intake job creates row
    pending --> composing : NotebookLM job started
    composing --> ready : audio + transcript returned
    ready --> published : episode appended to RSS, audio uploaded
    composing --> failed : NotebookLM error or timeout
    failed --> [*]
    published --> [*]
```

---

## Failure modes worth knowing

- **AI provider down** → synthesis job records a failed run; the previous
  day's brief stays visible. Operator can retry from the admin UI by editing
  the schedule or re-triggering via the orchestrator.
- **TTS quota exhausted** → filing is written but `narrated` step fails;
  briefing text is published without audio.
- **Storage backend unreachable** → publish step fails; the filing is already
  in the DB and will be picked up on the next successful publish.
- **Master key lost** → all encrypted settings (AI, TTS, GitHub, storage
  credentials) become unreadable; briefings, audio files, and snapshots are
  unaffected. Operator re-enters credentials through the setup wizard.
