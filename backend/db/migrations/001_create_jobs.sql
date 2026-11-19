-- Companies and the jobs collected from each source.
--
-- Rules the database enforces itself (so no bug in Python can break them):
--   * allowed values for source, arrangement, employment type and review status
--   * the same posting is never stored twice: UNIQUE (source, source_job_id)
--   * salary_max >= salary_min, scores between 0 and 100

CREATE TABLE companies (
    id      text PRIMARY KEY,
    name    text NOT NULL,
    website text
);

CREATE TABLE jobs (
    id               text PRIMARY KEY,
    source           text NOT NULL CHECK (source IN ('greenhouse', 'lever', 'adzuna', 'manual')),
    source_job_id    text NOT NULL,
    title            text NOT NULL,
    company_id       text NOT NULL REFERENCES companies (id),
    location         text,
    work_arrangement text NOT NULL CHECK (work_arrangement IN ('onsite', 'hybrid', 'remote', 'unknown')),
    employment_type  text NOT NULL CHECK (employment_type IN ('full_time', 'part_time', 'contract', 'temporary', 'internship', 'unknown')),
    description      text NOT NULL,
    url              text NOT NULL,
    salary_min       integer CHECK (salary_min >= 0),
    salary_max       integer CHECK (salary_max >= 0),
    salary_currency  text,
    posted_at        timestamptz,
    first_seen_at    timestamptz NOT NULL DEFAULT now(),
    last_seen_at     timestamptz NOT NULL DEFAULT now(),
    review_status    text NOT NULL DEFAULT 'new' CHECK (review_status IN ('new', 'shortlisted', 'dismissed')),
    skills           jsonb NOT NULL DEFAULT '[]',
    match            jsonb,          -- the score explanation shown on the job page
    match_score      integer CHECK (match_score BETWEEN 0 AND 100),  -- copy of match.score, for sorting
    UNIQUE (source, source_job_id),
    CHECK (salary_max >= salary_min)
);

CREATE INDEX jobs_review_status_idx ON jobs (review_status);
CREATE INDEX jobs_first_seen_at_idx ON jobs (first_seen_at DESC);
CREATE INDEX jobs_match_score_idx   ON jobs (match_score DESC NULLS LAST);
