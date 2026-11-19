-- Settings, plus the job-collection pipeline:
--   raw_postings   exactly what each source returned (kept for debugging and replays)
--   quarantine     postings that failed validation, with the reason
--   jobs           the clean records (001)
--   ingestion_runs one row per run per source: the counts shown in Settings

CREATE TABLE source_settings (
    source      text PRIMARY KEY CHECK (source IN ('greenhouse', 'lever', 'adzuna')),
    enabled     boolean NOT NULL DEFAULT false,
    identifiers text[] NOT NULL DEFAULT '{}'   -- board tokens, company slugs, or search terms
);

INSERT INTO source_settings (source) VALUES ('greenhouse'), ('lever'), ('adzuna');

CREATE TABLE app_settings (
    id            integer PRIMARY KEY DEFAULT 1 CHECK (id = 1),   -- exactly one row
    notifications jsonb NOT NULL,
    account       jsonb NOT NULL
);

INSERT INTO app_settings (notifications, account) VALUES (
    '{"daily_digest": false, "digest_hour": 7, "digest_min_score": 70, "follow_up_reminders": true}',
    '{"display_name": "", "email": "", "timezone": "America/Edmonton"}'
);

CREATE TABLE ingestion_runs (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source      text NOT NULL,
    started_at  timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status      text NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'succeeded', 'partial', 'failed')),
    fetched     integer NOT NULL DEFAULT 0,
    inserted    integer NOT NULL DEFAULT 0,
    updated     integer NOT NULL DEFAULT 0,
    skipped     integer NOT NULL DEFAULT 0,
    failed      integer NOT NULL DEFAULT 0,
    errors      jsonb NOT NULL DEFAULT '[]'
);

CREATE INDEX ingestion_runs_source_idx ON ingestion_runs (source, started_at DESC);

CREATE TABLE raw_postings (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id        bigint NOT NULL REFERENCES ingestion_runs (id) ON DELETE CASCADE,
    source        text NOT NULL,
    identifier    text NOT NULL,
    source_job_id text,
    payload       jsonb NOT NULL,
    fetched_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE quarantine (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id        bigint NOT NULL REFERENCES ingestion_runs (id) ON DELETE CASCADE,
    source        text NOT NULL,
    source_job_id text,
    payload       jsonb NOT NULL,
    reason        text NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
);

-- Change detection and cross-source duplicates for collected jobs.
ALTER TABLE jobs
    ADD COLUMN content_hash text,   -- hash of the fields that matter; a new hash = a real update
    ADD COLUMN dedupe_key   text;   -- company + title + city, normalized; same key = same job elsewhere

CREATE INDEX jobs_dedupe_key_idx ON jobs (dedupe_key);
