# Backend

The FastAPI server behind Waypoint: PostgreSQL for storage, real job
collection (Government of Alberta feeds, Ashby, Greenhouse, Lever, Adzuna),
explainable match scores, and every endpoint the website uses (docs/06).

**The full guide is [docs/09](../docs/09-backend.md)**: setup, connecting the
website, collecting jobs, scheduling, using the API from scripts, how it
works, and what's not built yet.

## Quick start

```
cd backend
docker compose up -d                      # PostgreSQL in Docker
python3 -m venv .venv                     # Windows: py -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cp .env.example .env                      # Windows: copy .env.example .env
python -m db.migrate                      # create the tables
uvicorn app.main:app --reload             # http://localhost:8000/docs
```

Then, in another terminal (venv active, `backend` folder):

```
python -m db.starter_sources              # turn on checked Alberta sources (fill in your profile first)
python -m app.ingestion.run               # collect jobs from the sources you turned on
pytest                                    # run the tests
```

## Stack

| Piece | Choice | Why |
| --- | --- | --- |
| Language | Python 3.12+ | |
| Web framework | FastAPI | Request validation and interactive docs at `/docs` |
| Data models | Pydantic v2 | Its JSON matches the frontend's field names exactly |
| Database | PostgreSQL 17, in Docker for development | |
| Database access | psycopg 3 with plain SQL | Every query is visible; the database enforces the key rules |
| Migrations | Numbered `.sql` files, applied by `db/migrate.py` | Just SQL |
| Job sources | Official public APIs only, via httpx | |
| Tests | pytest, against a separate `waypoint_test` database | |

## Layout

```
backend/
├── app/
│   ├── main.py, config.py, db.py, schemas.py, rows.py, util.py
│   ├── routers/        jobs, applications, dashboard, candidate, documents, settings, ingestion
│   ├── services/       matching (the score), rules (application statuses), storage (uploads)
│   └── ingestion/      run.py (the pipeline), check.py, skills.py, text.py, sources/ (greenhouse, lever, ashby, rss, adzuna)
├── db/
│   ├── migrations/     001 jobs, 002 profile, 003 documents + applications, 004 settings + ingestion, 005 more sources
│   ├── migrate.py      apply migrations (--reset starts over, --test for the test database)
│   ├── seed.py         fictional demo data, for trying things out only
│   └── init/           creates the test database on Docker's first start
├── tests/              about 150 tests; recorded job-board responses in fixtures/
├── docker-compose.yml  PostgreSQL
├── .env.example        copy to .env (never commit .env)
└── storage/            uploaded files (created on first upload; git ignores it)
```

## Status

| Done | Not yet |
| --- | --- |
| All 19 website operations, with the rules below enforced | Sign-in (needed before hosting it anywhere) |
| Collection from Government of Alberta feeds, Ashby, Greenhouse, Lever (checked live) and Adzuna: raw, quarantine, jobs; area and skip-word filters; change detection; cross-source duplicates; run log | Adzuna checked live (needs your key) |
| Match score (identical to the website's), re-scored when the profile changes | Email notifications |
| Private uploads (PDF/.docx, 5 MB), export, delete everything | AI cover letters, smarter matching |
| An HTTP API for other automations, including "collect now" | Hosting |

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
