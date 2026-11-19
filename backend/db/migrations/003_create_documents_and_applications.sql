-- Résumé and cover-letter versions, applications, and their timeline.

CREATE TABLE documents (
    id             text PRIMARY KEY,
    document_type  text NOT NULL CHECK (document_type IN ('resume', 'cover_letter')),
    title          text NOT NULL CHECK (btrim(title) <> ''),
    version        integer NOT NULL CHECK (version >= 1),
    status         text NOT NULL DEFAULT 'ready' CHECK (status IN ('draft', 'ready', 'archived')),
    origin         text NOT NULL CHECK (origin IN ('uploaded', 'generated')),
    related_job_id text REFERENCES jobs (id) ON DELETE SET NULL,
    file_name      text,             -- the name you uploaded it with
    size_bytes     integer CHECK (size_bytes >= 0),
    content_type   text,
    storage_key    text UNIQUE,      -- where the file is in private storage; never sent to the browser
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    -- versions count up per type, per job: résumé v1, v2, v3; each job's cover letter v1, v2
    UNIQUE NULLS NOT DISTINCT (document_type, related_job_id, version)
);

CREATE TABLE applications (
    id                       text PRIMARY KEY,
    job_id                   text NOT NULL UNIQUE REFERENCES jobs (id) ON DELETE CASCADE,  -- one per job
    status                   text NOT NULL DEFAULT 'saved' CHECK (status IN (
                                 'saved', 'preparing', 'ready_for_review', 'applied',
                                 'interview', 'offer', 'rejected', 'withdrawn')),
    status_source            text NOT NULL DEFAULT 'user' CHECK (status_source IN ('user', 'integration')),
    applied_at               date,
    follow_up_at             date,
    resume_document_id       text REFERENCES documents (id) ON DELETE SET NULL,
    cover_letter_document_id text REFERENCES documents (id) ON DELETE SET NULL,
    notes                    text NOT NULL DEFAULT '' CHECK (length(notes) <= 5000),
    created_at               timestamptz NOT NULL DEFAULT now(),
    updated_at               timestamptz NOT NULL DEFAULT now(),
    CHECK (follow_up_at >= applied_at),
    -- follow-ups only make sense while you're waiting to hear back
    CHECK (follow_up_at IS NULL OR status IN ('applied', 'interview'))
);

CREATE INDEX applications_status_idx     ON applications (status);
CREATE INDEX applications_updated_at_idx ON applications (updated_at DESC);

CREATE TABLE application_events (
    id             text PRIMARY KEY,
    application_id text NOT NULL REFERENCES applications (id) ON DELETE CASCADE,
    event_type     text NOT NULL CHECK (event_type IN (
                       'created', 'status_changed', 'submission_confirmed', 'note_updated',
                       'follow_up_set', 'document_linked', 'interview_scheduled')),
    occurred_at    timestamptz NOT NULL DEFAULT now(),
    summary        text NOT NULL,
    from_status    text,
    to_status      text,
    interview      jsonb            -- {scheduled_for, format, with_whom} for interview_scheduled
);

CREATE INDEX application_events_app_idx  ON application_events (application_id, occurred_at DESC);
CREATE INDEX application_events_time_idx ON application_events (occurred_at DESC);
