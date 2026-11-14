# Backend (planned)

The server behind Waypoint: it stores everything in PostgreSQL, collects job
postings on a schedule, scores them, and answers the website's requests.
**Nothing is built yet.** This folder holds the plan. The website already
works without it, on sample data.

## Stack

| Piece | Choice | Why |
| --- | --- | --- |
| Language | Python 3.12+ | |
| Web framework | FastAPI | Automatic request validation and interactive docs at `/docs` |
| Data models | Pydantic v2 | Its JSON matches the frontend's field names with no extra config |
| Database | PostgreSQL | |
| Database access | SQLAlchemy 2 + Alembic (migrations) | |
| Tests | pytest | |
| Scheduling | GitHub Actions cron first, Prefect later | Runs job collection daily |

## Planned folder layout

```
backend/
├── README.md                 this file
├── pyproject.toml            dependencies
├── .env.example              DATABASE_URL, ADZUNA_APP_ID, ... (never real values)
├── alembic/                  database migrations
├── app/
│   ├── main.py               FastAPI app, CORS, routers
│   ├── config.py             settings read from environment variables
│   ├── db.py                 database connection
│   ├── models/               SQLAlchemy tables
│   ├── schemas/              Pydantic request/response models (match docs/06)
│   ├── routers/              one file per area: jobs, applications, documents, ...
│   ├── services/
│   │   ├── matching.py       the match score (port of scoreJob in sample-data.js)
│   │   └── applications.py   status rules (port of frontend/js/lib/status.js)
│   └── ingestion/
│       ├── sources/          greenhouse.py, lever.py, adzuna.py
│       ├── normalize.py      raw posting → clean job record
│       └── run.py            one collection run, with a run log
└── tests/                    pytest, starting with the rules in tests/mock-api.test.js
```

## Data flow for job collection

```
Greenhouse / Lever / Adzuna APIs
        │  fetch (respecting rate limits and terms of use)
        ▼
raw_postings        the exact JSON each source returned, with a timestamp
        │  validate + normalize
        ├──► quarantine     records that failed validation, with the reason
        ▼
jobs                clean records; content_hash detects real changes
        │  score against the profile
        ▼
job_matches         the factors and points the job page shows
        │
ingestion_runs      one row per run: fetched, inserted, updated, skipped, failed
                    (shown in Settings → Sources on the website)
```

## Build order

Each step ends with the website using real data for one more area. Switch
operations over in `frontend/js/config.js` as you go
([docs/07](../docs/07-connecting-the-backend.md)).

1. **Hello API.** FastAPI app, CORS for `http://localhost:8080`, `GET /health`.
2. **Jobs, read-only.** `jobs` table, a seed script, `GET /api/v1/jobs` with
   the filters in [docs/06](../docs/06-api-contract.md), `GET /api/v1/jobs/{id}`.
   Turn on `listJobs`, `getJob`.
3. **Profile and scoring.** `GET/PUT /api/v1/candidate`; port `scoreJob()`;
   rescore when the profile changes.
4. **Applications.** All six application operations, with the status rules
   enforced server-side. Port `tests/mock-api.test.js` to pytest first, then
   make them pass.
5. **Dashboard metrics** as SQL queries.
6. **Real job collection.** Greenhouse and Lever first (public, no keys),
   then Adzuna; raw → quarantine → clean; run log; daily schedule.
7. **Documents** with private file storage (not in the database).
8. **Settings, export, delete.**
9. **Sign-in**, then host it on `https://` and point the published site at it.

## Rules the backend must keep

From [docs/06](../docs/06-api-contract.md), in short:

- One application per job (409 on a duplicate).
- "Applied" only via `POST /applications/{id}/confirm-submission`; a PATCH
  that tries to set it gets 422. Waypoint never submits applications.
- Only the allowed status moves; closed applications stay closed.
- Follow-ups only for applied/interviewing applications; cleared on close.
- Every change writes an application event (the timeline).
- Never invent data: no fabricated postings, skills or outcomes.
- Job descriptions from other sites are untrusted text; store and return them
  as text.
- Secrets (database URL, API keys) only in environment variables, never in
  the repository or in `frontend/`.
