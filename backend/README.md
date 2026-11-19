# Backend

The server behind Waypoint: it stores everything in PostgreSQL, collects job
postings on a schedule, scores them, and answers the website's requests.

**Status:** steps 1 and 2 are set up as guided exercises. The plumbing is
done; the SQL and the jobs endpoints are yours to write, with tests that say
when you're done. Start with [docs/09](../docs/09-backend-steps-1-2.md).

## Quick start

```
cd backend
docker compose up -d                      # PostgreSQL in Docker
python3 -m venv .venv                     # Windows: py -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cp .env.example .env                      # Windows: copy .env.example .env
python -m db.migrate                      # create the tables
python -m db.seed                         # load the fictional sample jobs
uvicorn app.main:app --reload             # http://localhost:8000/docs
pytest                                    # in a second terminal
```

## Stack

| Piece | Choice | Why |
| --- | --- | --- |
| Language | Python 3.12+ | |
| Web framework | FastAPI | Automatic request validation and interactive docs at `/docs` |
| Data models | Pydantic v2 | Its JSON matches the frontend's field names with no extra config |
| Database | PostgreSQL 17, in Docker for development | |
| Database access | psycopg 3 with plain SQL | You see and write every query; the skill data engineering uses daily |
| Migrations | Numbered `.sql` files, applied by `db/migrate.py` | No tool to learn; it's just SQL |
| Tests | pytest, against a separate `waypoint_test` database | |
| Scheduling | GitHub Actions cron first, Prefect later | Runs job collection daily |

## Folder layout

```
backend/
├── README.md                  this file
├── requirements.txt           what the API needs to run
├── requirements-dev.txt       plus the test tools
├── .env.example               copy to .env (never commit .env)
├── docker-compose.yml         PostgreSQL for development
├── pytest.ini                 test settings
├── app/
│   ├── main.py                FastAPI app, CORS, /health, routers
│   ├── config.py              settings from .env
│   ├── db.py                  one connection per request
│   ├── schemas.py             request/response shapes (match docs/06)
│   ├── rows.py                database row → Job
│   └── routers/
│       └── jobs.py            GET /jobs, GET /jobs/{id}, PATCH /jobs/{id}   ← exercise
├── db/
│   ├── migrate.py             applies migrations/*.sql once each, in order
│   ├── seed.py                loads seed/jobs.json (fictional data)
│   ├── migrations/
│   │   └── 001_create_jobs.sql   companies + jobs tables               ← exercise
│   ├── seed/jobs.json         same sample jobs the website uses
│   └── init/                  runs once when the Docker database is first created
└── tests/
    ├── conftest.py            fresh test database for every test
    ├── test_step1_health.py
    ├── test_step2a_schema.py
    └── test_step2_jobs_api.py
```

Coming later: `app/services/` (matching, application rules) and
`app/ingestion/` (Greenhouse, Lever, Adzuna collectors).

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
   *Set up.*
2. **Jobs.** `jobs` table, a seed script, `GET /api/v1/jobs` with the filters
   in [docs/06](../docs/06-api-contract.md), `GET /api/v1/jobs/{id}`,
   `PATCH /api/v1/jobs/{id}`. Turn on `listJobs`, `getJob`, `updateJobStatus`.
   *Exercise: [docs/09](../docs/09-backend-steps-1-2.md).*
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
