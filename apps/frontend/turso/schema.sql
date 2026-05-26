-- Dispatch briefings schema for Turso (libSQL).
-- Applied once at setup; idempotent via IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS projects (
  slug TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  github_repo TEXT,
  local_path TEXT,
  status TEXT NOT NULL,
  kind TEXT,
  color_hint TEXT,
  summary TEXT,
  podcast_config TEXT,
  sort_order INTEGER DEFAULT 0,
  created_at TEXT,
  from_the_desk TEXT,
  from_the_desk_generated_at TEXT,
  first_seen_at TEXT,
  last_seen_at TEXT
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY,
  project_slug TEXT NOT NULL REFERENCES projects(slug),
  kind TEXT NOT NULL,
  external_id TEXT NOT NULL,
  title TEXT,
  body TEXT,
  url TEXT,
  author TEXT,
  occurred_at TEXT NOT NULL,
  ingested_at TEXT NOT NULL,
  meta TEXT,
  UNIQUE(project_slug, kind, external_id)
);
CREATE INDEX IF NOT EXISTS events_occurred ON events(occurred_at DESC);
CREATE INDEX IF NOT EXISTS events_project_occurred ON events(project_slug, occurred_at DESC);

CREATE TABLE IF NOT EXISTS cursors (
  project_slug TEXT NOT NULL REFERENCES projects(slug),
  source TEXT NOT NULL,
  cursor TEXT,
  updated_at TEXT NOT NULL,
  PRIMARY KEY(project_slug, source)
);

CREATE TABLE IF NOT EXISTS filings (
  id INTEGER PRIMARY KEY,
  date TEXT NOT NULL,
  kind TEXT NOT NULL,
  issue_no INTEGER,
  covers_from TEXT NOT NULL,
  covers_until TEXT NOT NULL,
  lead_headline TEXT,
  lead_body TEXT,
  lead_article TEXT,
  audio_url TEXT,
  audio_duration_s INTEGER,
  active_count INTEGER,
  project_lines TEXT,
  addendum_label TEXT,
  addendum_body TEXT,
  model TEXT NOT NULL,
  prompt_hash TEXT NOT NULL,
  generated_at TEXT NOT NULL,
  raw_response TEXT,
  UNIQUE(date, kind)
);

CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY,
  job TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  events_added INTEGER,
  error TEXT
);

CREATE TABLE IF NOT EXISTS briefing_mentions (
  briefing_date TEXT NOT NULL,
  project_slug TEXT NOT NULL REFERENCES projects(slug),
  excerpt TEXT NOT NULL,
  position INTEGER NOT NULL,
  PRIMARY KEY (briefing_date, project_slug, position)
);
CREATE INDEX IF NOT EXISTS briefing_mentions_project ON briefing_mentions(project_slug, briefing_date DESC);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS schedules (
  job_name TEXT PRIMARY KEY,
  cron_expression TEXT NOT NULL,
  timezone TEXT NOT NULL DEFAULT 'UTC',
  is_enabled INTEGER NOT NULL DEFAULT 1,
  last_run_at TEXT,
  next_run_at TEXT
);

CREATE TABLE IF NOT EXISTS system (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
