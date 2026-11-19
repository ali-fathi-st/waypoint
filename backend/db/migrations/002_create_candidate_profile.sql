-- Your profile: what the match score compares each job against.
-- One profile (Waypoint is single-user for now). Lists that are just text
-- use text[]; lists of records get their own table, kept in order by position.

CREATE TABLE candidate_profile (
    id                text PRIMARY KEY,
    full_name         text NOT NULL DEFAULT '',
    email             text NOT NULL DEFAULT '',
    headline          text NOT NULL DEFAULT '',
    summary           text NOT NULL DEFAULT '',
    preferred_titles  text[] NOT NULL DEFAULT '{}',
    locations         text[] NOT NULL DEFAULT '{}',
    work_arrangements text[] NOT NULL DEFAULT '{}'
                      CHECK (work_arrangements <@ ARRAY['onsite', 'hybrid', 'remote']),
    salary_min        integer CHECK (salary_min >= 0),
    salary_max        integer CHECK (salary_max >= 0),
    salary_currency   text NOT NULL DEFAULT 'CAD',
    exclusions        text[] NOT NULL DEFAULT '{}',
    updated_at        timestamptz NOT NULL DEFAULT now(),
    CHECK (salary_max >= salary_min)
);

CREATE TABLE candidate_skills (
    profile_id  text NOT NULL REFERENCES candidate_profile (id) ON DELETE CASCADE,
    position    integer NOT NULL,
    name        text NOT NULL,
    proficiency text NOT NULL CHECK (proficiency IN ('familiar', 'proficient', 'expert')),
    years       numeric(4, 1) CHECK (years >= 0),
    PRIMARY KEY (profile_id, position)
);

CREATE TABLE candidate_experience (
    id          text PRIMARY KEY,
    profile_id  text NOT NULL REFERENCES candidate_profile (id) ON DELETE CASCADE,
    position    integer NOT NULL,
    title       text NOT NULL,
    company     text NOT NULL,
    start_month text NOT NULL CHECK (start_month ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    end_month   text CHECK (end_month ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    description text NOT NULL DEFAULT '',
    CHECK (end_month >= start_month)
);

CREATE TABLE candidate_education (
    id          text PRIMARY KEY,
    profile_id  text NOT NULL REFERENCES candidate_profile (id) ON DELETE CASCADE,
    position    integer NOT NULL,
    institution text NOT NULL,
    credential  text NOT NULL,
    field       text,
    end_month   text CHECK (end_month ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    in_progress boolean NOT NULL DEFAULT false
);

-- Start with an empty profile so GET /candidate always has something to return.
INSERT INTO candidate_profile (id) VALUES ('me');
