# 6. API contract

What the frontend expects from the FastAPI backend: every endpoint, every
field, every rule. Build the backend to match this and the site works
without changing a line of frontend code.

**Two ways to check your backend against it:**

- `frontend/js/api/contract.js` lists the fields each record must have. When
  connected, the site checks every reply and names any missing field, e.g.
  `GET /jobs: item 0 is missing "first_seen_at"`.
- The sample data (`frontend/js/data/sample-data.js`) is a complete, working
  example of every record. The examples below are copied from it.

All routes start with `/api/v1`. The frontend sends cookies
(`credentials: "include"`), so login sessions work once you add sign-in.

## Conventions

| Thing | Format | Example |
| --- | --- | --- |
| Field names | snake_case (Pydantic default; no aliases needed) | `first_seen_at` |
| IDs | strings (use UUIDs) | `"0b5e…"` |
| Timestamps | ISO 8601, UTC | `"2026-11-10T15:04:00Z"` |
| Calendar dates | `YYYY-MM-DD` | `applied_at`, `follow_up_at` |
| Months | `YYYY-MM` | experience `start_month` |
| Missing values | `null`, never omitted or `""` | `"salary_min": null` |
| Money | whole number in the stated currency | `85000` |

Pydantic v2 serializes `datetime` as ISO 8601 and `date` as `YYYY-MM-DD`, so
`datetime` and `date` fields in your response models already match.

## Errors

Use FastAPI's default error bodies. The frontend (`js/api/http-api.js`) reads both forms:

```json
{ "detail": "Job not found" }
{ "detail": [{ "loc": ["body", "follow_up_at"], "msg": "Input should be a valid date", "type": "date_parsing" }] }
```

| Status | Meaning in the UI |
| --- | --- |
| 404 | "Not found" state for that record |
| 409 | Conflict, e.g. an application already exists for the job |
| 400 / 422 | Validation. Field messages appear under the matching form field |
| 401 / 403 | "Not signed in" message |
| 5xx | Retryable error with a "Try again" button (retried once automatically) |

## Endpoints

### Health

| Method | Route | Returns |
| --- | --- | --- |
| GET | `/health` | `{"status": "ok"}`. Not under `/api/v1`, and the frontend doesn't call it; it's for your deploy checks. |

### Jobs

| Method | Route | Body | Returns |
| --- | --- | --- | --- |
| GET | `/api/v1/jobs` | query params below | `Paginated<Job>` |
| GET | `/api/v1/jobs/{id}` | none | `Job`, or 404 |
| PATCH | `/api/v1/jobs/{id}` | `{"review_status": "new" \| "shortlisted" \| "dismissed"}` | `Job` |

`GET /api/v1/jobs` query parameters (all optional):

| Param | Type | Behaviour |
| --- | --- | --- |
| `q` | string | case-insensitive match on title |
| `company` | string | case-insensitive match on company name |
| `location` | string | match on location; `remote` also matches remote jobs |
| `source` | `greenhouse` \| `lever` \| `adzuna` \| `manual` | exact |
| `found_after` | ISO timestamp | `first_seen_at >= found_after` |
| `min_score` | 0–100 | `match.score >= min_score` |
| `review_status` | `active` (default) \| `new` \| `shortlisted` \| `dismissed` \| `all` | `active` = new + shortlisted |
| `sort` | `match` (default) \| `newest` \| `posted` | match = score desc, then newest |
| `limit` | int, default 20 | page size |
| `offset` | int, default 0 | |

`Paginated<T>` is `{"items": [...], "total": 42, "limit": 20, "offset": 0}`.
`total` counts all matches, not just this page.

`Job.match` is the explanation shown on the job page: `factors` each have a
`weight` (they sum to 1) and a `score` (0–1), and `score` = round(sum of
weight × score × 100). `scoreJob()` in `frontend/js/data/sample-data.js` is a
working version to port to Python. `match` may be `null` until scoring has run.

Job ingestion (`POST /api/v1/jobs` in the guide) is between your pipeline and
the API. The frontend never calls it.

### Applications

| Method | Route | Body | Returns |
| --- | --- | --- | --- |
| GET | `/api/v1/applications` | query `status`, `q` | `Application[]`, newest change first |
| GET | `/api/v1/applications/{id}` | none | `Application` with `events` |
| POST | `/api/v1/applications` | `{"job_id": "...", "notes": "optional"}` | `Application` (201 is fine) |
| PATCH | `/api/v1/applications/{id}` | any of `status`, `notes`, `follow_up_at`, `resume_document_id`, `cover_letter_document_id` | `Application` |
| POST | `/api/v1/applications/{id}/confirm-submission` | `{"applied_at", "resume_document_id", "cover_letter_document_id", "follow_up_at"}` | `Application` |
| POST | `/api/v1/applications/{id}/interviews` | `{"scheduled_for", "format", "with_whom"}` | `Application` |

Rules to enforce in the API (the UI relies on them; `tests/mock-api.test.js`
checks the mock's versions, so port those tests to Python too):

1. **One application per job.** A second `POST` for the same `job_id` returns 409.
   Creating one sets the job's `application_id`, and a `new` job becomes `shortlisted`.
2. **`applied` only through `confirm-submission`.** `PATCH` with
   `"status": "applied"` returns 422. This endpoint records that the user
   submitted the application themselves. Nothing is ever sent to an employer.
3. **Allowed transitions** (`STATUS_TRANSITIONS` in `frontend/js/lib/status.js`):

   | From | To (by PATCH) |
   | --- | --- |
   | saved | preparing, withdrawn |
   | preparing | saved, ready_for_review, withdrawn |
   | ready_for_review | preparing, withdrawn |
   | applied | interview, offer, rejected, withdrawn |
   | interview | offer, rejected, withdrawn |
   | offer | rejected, withdrawn |
   | rejected, withdrawn | none (closed) |

   `confirm-submission` is allowed from saved, preparing or ready_for_review.
   Anything else returns 422.
4. **Follow-ups** only exist for `applied` and `interview`. Moving to any
   other status sets `follow_up_at` to `null` and records an event.
   `applied_at` can't be in the future, and `follow_up_at` can't be before `applied_at`.
5. **Adding an interview** to an `applied` application moves it to `interview`.
   It's allowed only for `applied` or `interview`.
6. **Every change writes an `ApplicationEvent`** (`created`, `status_changed`,
   `submission_confirmed`, `note_updated`, `follow_up_set`, `document_linked`,
   `interview_scheduled`) with a one-line `summary`. `status_source` is `user`
   unless a verified integration set it.
7. Linked document IDs must exist and match the type (a cover letter can't be
   linked as a résumé). Otherwise 422.

### Dashboard

| Method | Route | Returns |
| --- | --- | --- |
| GET | `/api/v1/dashboard/metrics` | `DashboardMetrics` |

Definitions (compute them with SQL; they're good practice for the Gold layer):

- `applications_submitted`: status in applied, interview, offer, rejected, plus withdrawn with an `applied_at`
- `interviews`: reached the interview stage (status interview/offer, or an interview event)
- `responses`: submitted applications that got any reply (interview, offer or rejection)
- `response_rate`: `responses / applications_submitted`, or `null` when nothing is submitted
- `follow_ups_due`: applied/interview with `follow_up_at <= today`
- `jobs_found_by_day`: last 14 calendar days, oldest first, including zero days
- `jobs_to_review`: top 5 `new` jobs by score
- `recent_activity`: latest 8 application events, each with `job_title` and `company_name`

### Candidate profile

| Method | Route | Body | Returns |
| --- | --- | --- | --- |
| GET | `/api/v1/candidate` | none | `CandidateProfile` |
| PUT | `/api/v1/candidate` | the full profile without `id` and `updated_at` | `CandidateProfile` |

Saving the profile should trigger re-scoring, because scores depend on it. The
UI refetches jobs after a save.

### Documents

| Method | Route | Body | Returns |
| --- | --- | --- | --- |
| GET | `/api/v1/documents` | query `document_type`, `include_archived` | `Document[]` |
| POST | `/api/v1/documents` | `multipart/form-data`: `document_type`, `title`, `related_job_id?`, `file` | `Document` |
| PATCH | `/api/v1/documents/{id}` | `{"title"?, "status"?}` | `Document` |

`version` increments per `document_type`. Accept PDF and DOCX up to 5 MB (the
frontend checks too, but the API must enforce it). Store files in private
object storage, never in the response. The frontend never needs a file URL in
this version.

### Settings and data

| Method | Route | Body | Returns |
| --- | --- | --- | --- |
| GET | `/api/v1/settings` | none | `Settings` |
| PATCH | `/api/v1/settings` | any of `sources`, `notifications`, `account` | `Settings` |
| GET | `/api/v1/export` | none | JSON file of all user data |
| DELETE | `/api/v1/data` | none | 204 |

`sources[].last_run_*` come from your ingestion run log (records fetched,
inserted, updated, skipped, failed). Credentials such as Adzuna keys stay in
backend environment variables. The API only reports
`credentials_configured: true/false`.


## Example records

These are real records from the sample data (shortened where marked).
Pydantic models with the same field names produce exactly this JSON.

### Job (`GET /api/v1/jobs/{id}`, and each item of `GET /api/v1/jobs`)

`skills`, `match.factors` and `description` are shortened here.

```json
{
  "id": "job_002",
  "source": "lever",
  "source_job_id": "lever-4107",
  "title": "Analytics Engineer",
  "company": {
    "id": "co_kestrel",
    "name": "Kestrel Insurance Group",
    "website": "https://kestrel.example.com"
  },
  "location": "Calgary, AB",
  "work_arrangement": "hybrid",
  "employment_type": "full_time",
  "description": "Kestrel's analytics team supports pricing and claims with a modern warehouse and a small, senior-friendly team.\n\nWhat you'll do\n...",
  "url": "https://jobs.example.com/kestrel/4107",
  "salary_min": 90000,
  "salary_max": 110000,
  "salary_currency": "CAD",
  "posted_at": "2026-11-13T18:00:00.000Z",
  "first_seen_at": "2026-11-14T12:16:00.000Z",
  "last_seen_at": "2026-11-14T12:15:00.000Z",
  "review_status": "new",
  "skills": [
    {
      "name": "SQL",
      "required": true,
      "evidence": "Working experience with SQL"
    },
    {
      "name": "dbt",
      "required": true,
      "evidence": "Working experience with dbt"
    }
  ],
  "match": {
    "job_id": "job_002",
    "score": 79,
    "summary": "Missing 1 required skill: dbt.",
    "factors": [
      {
        "key": "required_skills",
        "label": "Required skills",
        "weight": 0.4,
        "score": 0.6666666666666666,
        "detail": "2 of 3 required skills on your profile"
      },
      {
        "key": "preferred_skills",
        "label": "Nice-to-have skills",
        "weight": 0.15,
        "score": 0.5,
        "detail": "1 of 2 nice-to-have skills"
      }
    ],
    "matched_skills": [
      "SQL",
      "Python",
      "Power BI"
    ],
    "missing_skills": [
      "dbt",
      "Snowflake"
    ],
    "method": "rules",
    "computed_at": "2026-11-14T16:00:00.000Z"
  },
  "application_id": null
}
```

### Application (`GET /api/v1/applications/{id}`)

`events` is newest first, and shortened here to two.

```json
{
  "id": "app_005",
  "job_id": "job_015",
  "job": {
    "title": "Junior Data Engineer",
    "company_name": "Ravine Logistics",
    "location": "Edmonton, AB",
    "url": "https://jobs.example.com/ravine/4198",
    "source": "lever"
  },
  "status": "interview",
  "status_source": "user",
  "applied_at": "2026-11-05",
  "follow_up_at": "2026-11-19",
  "resume_document_id": "doc_002",
  "cover_letter_document_id": null,
  "notes": "Hiring manager is the analytics lead.",
  "created_at": "2026-11-06T01:00:00.000Z",
  "updated_at": "2026-11-13T21:00:00.000Z",
  "events": [
    {
      "id": "evt_0015",
      "application_id": "app_005",
      "event_type": "interview_scheduled",
      "occurred_at": "2026-11-13T21:00:00.000Z",
      "summary": "Video interview scheduled",
      "from_status": null,
      "to_status": null,
      "interview": {
        "scheduled_for": "2026-11-16T16:00:00.000Z",
        "format": "video",
        "with_whom": "Analytics lead and one engineer"
      }
    },
    {
      "id": "evt_0014",
      "application_id": "app_005",
      "event_type": "status_changed",
      "occurred_at": "2026-11-13T02:10:00.000Z",
      "summary": "Status changed to interview",
      "from_status": "applied",
      "to_status": "interview",
      "interview": null
    }
  ]
}
```

### Document

```json
{
  "id": "doc_003",
  "document_type": "resume",
  "title": "Data-focused résumé (pipelines first)",
  "version": 3,
  "status": "ready",
  "origin": "uploaded",
  "related_job_id": null,
  "related_job_title": null,
  "file_name": "jordan-lee-resume-data-v3.pdf",
  "size_bytes": 155310,
  "created_at": "2026-11-08T15:00:00.000Z",
  "updated_at": "2026-11-08T15:00:00.000Z"
}
```

### Candidate profile (pieces)

The profile has `id`, `full_name`, `email`, `headline`, `summary`,
`preferred_titles` (list of text), `locations`, `work_arrangements`
(`onsite` / `hybrid` / `remote`), `salary_min`, `salary_max`,
`salary_currency`, `exclusions`, `updated_at`, and three lists:

One skill:

```json
{
  "name": "Python",
  "proficiency": "proficient",
  "years": 3
}
```

One experience entry (`end_month: null` means current role):

```json
{
  "id": "exp_1",
  "title": "IT Business Coordinator",
  "company": "Riverbend Health Services",
  "start_month": "2025-02",
  "end_month": null,
  "description": "Built Power Automate flows for staff onboarding and offboarding. Maintains Power BI reporting and SharePoint ticket tracking for a contact centre."
}
```

One education entry:

```json
{
  "id": "edu_1",
  "institution": "Northern Plains University",
  "credential": "BSc",
  "field": "Computing and Information Systems",
  "end_month": "2026-12",
  "in_progress": true
}
```

### Settings (pieces)

`sources` is a list, one per job source:

```json
{
  "source": "lever",
  "enabled": true,
  "identifiers": [
    "kestrel",
    "ravine",
    "lumen"
  ],
  "last_run_at": "2026-11-14T12:16:00.000Z",
  "last_run_status": "partial",
  "last_run_summary": {
    "fetched": 96,
    "inserted": 1,
    "updated": 4,
    "skipped": 89,
    "failed": 2
  },
  "credentials_configured": true
}
```

```json
{
  "notifications": {
    "daily_digest": true,
    "digest_hour": 7,
    "digest_min_score": 70,
    "follow_up_reminders": true
  },
  "account": {
    "display_name": "Jordan",
    "email": "jordan.lee@example.com",
    "timezone": "America/Edmonton"
  }
}
```

## A first endpoint in FastAPI

Enough to connect `listJobs` in hybrid mode (see
[07](07-connecting-the-backend.md)). It's only an outline; the guide in
`backend/README.md` covers the database.

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Waypoint API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "https://ali-fathi-st.github.io"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/v1/jobs")
def list_jobs(limit: int = 20, offset: int = 0, review_status: str = "active", sort: str = "match"):
    jobs = []  # later: query PostgreSQL
    return {"items": jobs[offset:offset + limit], "total": len(jobs), "limit": limit, "offset": offset}
```

## CORS

The browser calls the API directly, so FastAPI must allow the site's
address. It must list addresses explicitly: `allow_origins=["*"]` doesn't work
with cookies.

| Where the site runs | Origin to allow |
| --- | --- |
| Your computer | `http://localhost:8080` (whatever port you use) |
| GitHub Pages | `https://ali-fathi-st.github.io` (no `/waypoint` path: an origin never includes one) |

Next: [07 Connecting the backend](07-connecting-the-backend.md)
