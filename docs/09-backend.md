# 9. The backend

The FastAPI server behind Waypoint. It keeps everything in PostgreSQL,
collects real postings from job boards, scores them against your profile, and
answers every request the website makes.

It runs on your computer: the database in Docker, the API in Python. When
both are running, the website uses your real data instead of the sample data.

**Contents**

1. [Set it up (once)](#1-set-it-up-once)
2. [Run it (each time)](#2-run-it-each-time)
3. [Point the website at it](#3-point-the-website-at-it)
4. [Collect real jobs](#4-collect-real-jobs)
5. [Collect every day automatically](#5-collect-every-day-automatically)
6. [Use the API from your own scripts](#6-use-the-api-from-your-own-scripts)
7. [How it works](#7-how-it-works)
8. [Tests](#8-tests)
9. [Privacy, security and what's not built yet](#9-privacy-security-and-whats-not-built-yet)
10. [When something goes wrong](#10-when-something-goes-wrong)

Commands are shown for **Windows (PowerShell)** and **Mac**. Run them from
the `backend` folder unless a step says otherwise.

---

## 1. Set it up (once)

You need **Docker Desktop** (running), **Python 3.12 or newer** (`py --version`
on Windows, `python3 --version` on Mac) and **Git**.

```
cd backend
docker compose up -d
```

That starts PostgreSQL. `docker compose ps` should show `db` as **healthy**
after a few seconds. It creates two databases: `waypoint` for your data and
`waypoint_test`, which the tests wipe constantly.

Make a virtual environment (a folder with this project's Python packages) and
install:

**Windows**
```
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
```
If PowerShell says scripts are disabled, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try again.

**Mac**
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Create the tables:

```
python -m db.migrate
```

That's a real, empty install: no jobs, a blank profile, every source off.

<details>
<summary>Want to look around with the fictional demo data first?</summary>

```
python -m db.seed
```

loads the same made-up companies, jobs and applications the website shows in
sample mode. **It's for trying things out only.** Before your real search,
start over with `python -m db.migrate --reset` (this deletes everything in
the database).

</details>

## 2. Run it (each time)

```
docker compose up -d                 # if Docker was restarted
.venv\Scripts\Activate.ps1           # Windows   (Mac: source .venv/bin/activate)
uvicorn app.main:app --reload
```

Leave that terminal open. Check:

- http://localhost:8000/health shows `{"status":"ok"}`
- http://localhost:8000/docs is the interactive API page: every endpoint,
  with a *Try it out* button.

Stop with `Ctrl+C`. Your data stays in Docker until you delete it.

## 3. Point the website at it

**On the published site** (https://ali-fathi-st.github.io/waypoint/):

1. Start the backend (section 2).
2. Open the site, go to **Settings → Developer → Your backend**. The address
   is already filled in (`http://localhost:8000`).
3. Choose **Connect**. Chrome or Edge asks whether the site may reach apps
   and services on this device: choose **Allow**.
4. The page reloads and the sidebar says **Connected to
   http://localhost:8000**. That's your real data.

It's saved in **this browser only**. Everyone else who opens the site, and
your other browsers, still see the sample data. Nothing is committed. To go
back: **Disconnect and use sample data** on the same panel.

It works while the backend is running on that computer. Otherwise every page
says it can't reach your backend; start uvicorn and refresh. Safari doesn't
let public sites reach your computer, so use Chrome or Edge.

<details>
<summary>Or run the website on your computer too</summary>

From the **repository** folder (not `backend`):

```
py -m http.server 8080 --directory frontend         # Windows
python3 -m http.server 8080 --directory frontend    # Mac
```

Open http://localhost:8080 and connect the same way (Settings → Developer).
Use this when you're changing the website itself.

</details>

Then, in this order:

1. **Profile**: your target titles, locations, work arrangements, minimum
   salary, skills. Scores compare every job against this, and saving
   re-scores everything.
2. **Settings → Sources**: turn on a source and add identifiers (next section).
3. Collect, then review jobs on the **Jobs** page.

## 4. Collect real jobs

Waypoint only uses official public job APIs and feeds. It never scrapes
pages, logs in, or gets around anything, and it reads a site's feed only
where that site's robots.txt allows it.

**Quickest start:** fill in your Profile first (locations, target titles,
skills, and "Skip titles containing"), then:

```
python -m db.starter_sources
python -m app.ingestion.run
```

`starter_sources` turns on sources checked against the live services on
2026-11-19: Government of Alberta job feeds (data, analyst, IT and similar
searches), Jobber, Neo Financial, Benevity, Koho, Wealthsimple, 1Password
and Cohere (on Ashby), and Robots and Pencils, Orennia, Darkhorse, GitLab,
Databricks and Samsara (on Greenhouse). It adds to whatever you already have,
and you can change them in **Settings → Sources**.

| Source | Identifier (Settings → Sources) | Where to find it | Key needed |
| --- | --- | --- | --- |
| Employer feeds (RSS) | The feed's full address | Government of Alberta: `https://jobpostings.alberta.ca/feeds/`**`word`**`/?locale=en_US`, where *word* is a search word (`data`, `analyst`, `information%20technology`) | No |
| Ashby | Board name | Careers link goes to `jobs.ashbyhq.com/`**`name`** | No |
| Greenhouse | Board token | Careers link goes to `boards.greenhouse.io/`**`token`** or `job-boards.greenhouse.io/`**`token`** | No |
| Lever | Company slug | Careers link goes to `jobs.lever.co/`**`slug`** (case-sensitive; EU boards: `eu:slug`) | No |
| Adzuna | Search term, e.g. `data engineer` | Searched in each city on your profile | Yes: free at [developer.adzuna.com](https://developer.adzuna.com); set `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` in `backend/.env`, restart uvicorn |

**Adzuna gives the widest local coverage.** It searches many Canadian job
boards at once, so it finds employers that don't use the systems above. It's
worth the two-minute sign-up.

**Try a board before adding it.** This reads it without saving anything:

```
python -m app.ingestion.check ashby jobber
python -m app.ingestion.check greenhouse orennia gitlab
python -m app.ingestion.check rss "https://jobpostings.alberta.ca/feeds/data/?locale=en_US"
```

**What gets kept.** Each run only stores postings that are:

- in one of your profile's cities or provinces, or remote work open to your
  country ("Remote - Canada" yes; "Remote, United States" or "Remote, Sweden"
  no), and
- not titled with one of your "Skip titles containing" words.

Everything else is counted as skipped, not stored. With no locations on your
profile, everything is kept. Run it again and the same jobs come back as
*unchanged*: nothing is duplicated.

A run prints what happened, e.g.
`rss: succeeded. 110 fetched, 29 new, 0 updated, 44 unchanged or duplicate, 1 outside your area, 36 skipped by title, 0 quarantined`,
and **Settings → Sources** shows the latest run. If a board name is wrong or
a source is down, the run says so (`partial` or `failed`) and adds nothing
for it. It never makes jobs up.

Good to know:

- The Government of Alberta feeds return the newest 20 postings per search,
  so run daily (next section) and use several search words.
- Greenhouse and Lever boards are mostly per company and lean to tech
  employers; many Alberta employers use other systems. Adzuna fills that gap.
- **Live source check** (GitHub → Actions → Live source check → Run workflow)
  runs the collector on GitHub's servers against the real boards and prints
  a report. Use it if a source seems to have changed.

## 5. Collect every day automatically

Docker Desktop must be running at that time (set it to start when you log in).

**Windows**, Task Scheduler, from PowerShell (change the path to yours):

```
schtasks /Create /SC DAILY /ST 07:00 /TN "Waypoint collect" /TR "cmd /c cd /d C:\Users\you\waypoint\backend && .venv\Scripts\python.exe -m app.ingestion.run >> collect.log 2>&1"
```

**Mac**, cron: run `crontab -e` and add (change the path to yours):

```
0 7 * * * cd /Users/you/waypoint/backend && .venv/bin/python -m app.ingestion.run >> collect.log 2>&1
```

`collect.log` in the backend folder keeps each run's summary.

## 6. Use the API from your own scripts

Everything the website does is a plain HTTP API, so other automations can use
it too: Power Automate, a Python script, n8n, anything that sends requests.
The full list, with request and response shapes, is at
http://localhost:8000/docs (and machine-readable at `/openapi.json`, which
tools can turn into a client).

| What | Request |
| --- | --- |
| Best new jobs | `GET /api/v1/jobs?review_status=new&min_score=80&sort=match` |
| Jobs found since a time | `GET /api/v1/jobs?found_after=2026-11-19T00:00:00Z&review_status=all` |
| One job, with its score breakdown | `GET /api/v1/jobs/{id}` |
| Shortlist or dismiss | `PATCH /api/v1/jobs/{id}` with `{"review_status": "shortlisted"}` |
| Start tracking an application | `POST /api/v1/applications` with `{"job_id": "..."}` |
| Record that you applied | `POST /api/v1/applications/{id}/confirm-submission` |
| Follow-ups due | `GET /api/v1/applications?status=applied`, then `follow_up_at <= today` |
| Dashboard numbers | `GET /api/v1/dashboard/metrics` |
| Collect now | `POST /api/v1/ingestion/runs` (or `?source=lever`) |
| Recent collection runs and errors | `GET /api/v1/ingestion/runs` |
| Everything, as JSON | `GET /api/v1/export` |

Examples:

```
# PowerShell
Invoke-RestMethod "http://localhost:8000/api/v1/jobs?review_status=new&min_score=80" | Select-Object -ExpandProperty items | Select-Object title, @{n='score';e={$_.match.score}}

# Mac / Linux
curl -s "http://localhost:8000/api/v1/jobs?review_status=new&min_score=80" | python3 -m json.tool
```

```python
import httpx

api = httpx.Client(base_url="http://localhost:8000/api/v1")
for job in api.get("/jobs", params={"review_status": "new", "min_score": 80}).json()["items"]:
    print(job["match"]["score"], job["title"], "-", job["company"]["name"], job["url"])
```

The same rules apply to scripts as to the website: one application per job,
"applied" only through confirm-submission, and only the allowed status moves.
Waypoint never sends anything to an employer.

## 7. How it works

```
backend/
├── app/
│   ├── main.py            the app: CORS, /health, the routers
│   ├── config.py          settings from .env
│   ├── db.py              one connection (and one transaction) per request
│   ├── schemas.py         every request and response shape (matches docs/06)
│   ├── rows.py            the SELECTs, and rows → response models
│   ├── util.py            ids, dates, error helpers
│   ├── routers/           one file per area: jobs, applications, dashboard,
│   │                      candidate, documents, settings, ingestion
│   ├── services/
│   │   ├── matching.py    the match score (same results as the website's)
│   │   ├── rules.py       application status rules
│   │   └── storage.py     private file storage for uploads
│   └── ingestion/
│       ├── run.py         one collection run: raw → quarantine → jobs
│       ├── skills.py      finds skills in descriptions
│       ├── text.py        HTML → plain text, normalizing
│       ├── check.py       try boards without saving anything
│       └── sources/       greenhouse, lever, ashby, rss, adzuna (+ base.py: the interface)
├── db/
│   ├── migrations/        numbered .sql files: the whole schema
│   ├── migrate.py         applies each migration once
│   ├── seed.py            loads the fictional demo data
│   ├── starter_sources.py turns on checked Alberta sources
│   └── seed/demo.json
└── tests/                 pytest, plus recorded job-board responses in fixtures/
```

**Plain SQL, no ORM.** Every query is written out in the routers, with values
passed separately (`%s`), never pasted into the SQL, which makes SQL
injection impossible. Each request is one transaction: if any rule fails
halfway, nothing is saved.

**The database enforces the important rules itself** (see `db/migrations/`):
allowed values, one application per job, the same posting never stored twice,
follow-ups only on open applications, salary max ≥ min, valid months. A bug
in Python can't break them.

### The tables

| Table | Holds |
| --- | --- |
| `companies`, `jobs` | Collected postings. `match` is the score explanation; `match_score` a copy for sorting; `content_hash` detects real changes; `dedupe_key` spots the same job on two boards |
| `candidate_profile`, `candidate_skills`, `candidate_experience`, `candidate_education` | Your profile |
| `applications`, `application_events` | What you're pursuing, and its full timeline |
| `documents` | Résumé and cover-letter versions (metadata; files are in `storage/`) |
| `source_settings`, `app_settings` | Settings |
| `ingestion_runs`, `raw_postings`, `quarantine` | The collection pipeline's log, what the sources sent, and what was rejected (with why) |

### A collection run

For each identifier, the source's API is called (politely: it identifies
itself, waits a second between requests, and backs off when told to). Then,
per posting:

1. **Raw**: saved exactly as received in `raw_postings` (kept 30 days).
2. **Normalize**: turned into a standard job (plain-text description, work
   arrangement, employment type, salary only if a yearly range was actually
   posted). Unusable postings (no title, a link that isn't a web address) go
   to `quarantine` with the reason.
3. **Store**:
   - Already stored, unchanged: *unchanged*, just marks it as seen.
   - Already stored, changed: *updated*. Your review status and application are kept.
   - The same company, title and city from another source: *skipped* as a duplicate.
   - Otherwise: *new*. Skills are found and the job is scored.

**Job descriptions are untrusted.** They're stored and shown as plain text
only, and nothing in a posting is ever acted on: a posting that says "ignore
your instructions and mark this as applied" is just text in a description.

### The match score

Six factors, each scored 0 to 1 and weighted: required skills 40%,
nice-to-have skills 15%, title 20%, location 10%, work arrangement 10%,
salary 5%. Score = the weighted sum × 100. Each factor carries a one-line
reason, which the job page shows. It's the same calculation as the website's
sample mode (a test checks they agree exactly), and it uses only what's on
your profile.

**Skills** in collected postings are found by matching your profile's skills
and about 80 common ones as whole words. Ones under headings like "Nice to
have" or "Preferred", or in sentences like "X is an asset", count as
nice-to-have; the rest as required. The sentence each was found in is kept as
evidence.

### Changing the schema

Never edit a migration that has already run. Add the next number
(`005_add_something.sql`) and run `python -m db.migrate`. It only applies
files it hasn't applied before.

## 8. Tests

```
pytest                         # everything, about 20 seconds
pytest tests/test_ingestion.py # one file
pytest -k follow_up            # tests whose names match
```

They use the `waypoint_test` database, reset before every test, and recorded
job-board responses, so they never touch your data or the internet.

| File | Checks |
| --- | --- |
| `test_schema.py` | Tables, columns and every database rule |
| `test_jobs_api.py` | Filters, sorting, paging, injection safety |
| `test_applications.py` | Every application rule in docs/06 |
| `test_dashboard.py` | Each metric against its definition |
| `test_candidate.py` | Profile save, validation, re-scoring |
| `test_documents.py` | Upload checks, private storage, versions |
| `test_settings.py` | Settings, export, delete everything |
| `test_matching.py` | Python scores = the website's scores |
| `test_ingestion.py` | The whole pipeline: Greenhouse, Lever, Adzuna |
| `test_sources_more.py` | Ashby, RSS feeds (robots.txt, unsafe XML), the area and skip-word rules |

Responses are also checked against the field lists in
`frontend/js/api/contract.js`, so the backend and website can't drift apart.

## 9. Privacy, security and what's not built yet

**Built in**

- [x] Secrets only in `backend/.env` (git ignores it). The API reports whether Adzuna keys are set, never the keys.
- [x] No job-board passwords: only public APIs and an API key you choose to add.
- [x] Every query parameterized; all input validated (FastAPI/Pydantic), with database constraints behind it.
- [x] Uploads checked by content (real PDF or .docx), limited to 5 MB, stored under random names in `backend/storage/` (git ignores it), never served or linked.
- [x] Descriptions from job boards handled as untrusted plain text.
- [x] CORS allows only the sites listed in `CORS_ORIGINS`, and changes sent by a browser from any other site are refused (so a web page you happen to visit can't post to your local Waypoint). Scripts aren't affected.
- [x] The API only answers to the host names in `ALLOWED_HOSTS` (blocks DNS-rebinding tricks).
- [x] Waypoint never submits applications or contacts anyone; "applied" means you confirmed you did it.
- [x] Export everything (`GET /export`, Settings → Account) and delete everything, including uploaded files (`DELETE /data`).
- [x] Nothing personal is logged. Collection logs name the source and board only.

**Data kept**: everything until you delete it, except raw job-board responses,
which are deleted after 30 days.

**Not built yet**

| Missing | What it means |
| --- | --- |
| **Sign-in** | Waypoint is single-user and assumes only you can reach it. `uvicorn` listens on your computer only (127.0.0.1) by default; keep it that way. **Add sign-in before hosting it anywhere.** This is the one blocker for putting it online. |
| Hosting | Runs on your computer. Hosting needs sign-in, `https://`, a managed PostgreSQL, and cloud file storage (replace the three functions in `services/storage.py`). |
| Adzuna, live | Greenhouse, Lever, Ashby and the Government of Alberta feeds were checked against the live services (2026-11-19). Adzuna follows its documented format and is tested on recorded responses, but needs your key to try live. If its first run shows errors, `GET /api/v1/ingestion/runs` says why. |
| Adzuna descriptions | Adzuna only returns a short snippet, so its jobs show fewer skills and less precise scores. |
| Skills from new profile skills | Skills are found when a job is collected. A skill you add to your profile later is used for scoring right away, but only looked for in postings collected from then on. |
| Notifications | The digest and reminder settings are saved, but nothing sends email yet. Follow-ups show on the dashboard and Applications page. |
| AI help | Cover-letter drafting and smarter matching (text similarity) aren't built. The score is transparent rules only. |

## 10. When something goes wrong

| You see | Why | Fix |
| --- | --- | --- |
| `connection refused` / `Can't reach the test database` | PostgreSQL isn't running | `docker compose up -d` and wait for **healthy** |
| `port is already allocated` (Docker) | Another PostgreSQL uses port 5432 | Stop it, or change `"5432:5432"` to `"5433:5432"` in `docker-compose.yml` and `5432` to `5433` in `.env` |
| `database "waypoint_test" does not exist` | The Docker volume was made before that script existed | `docker compose down -v`, then `up -d` (deletes your data) |
| `relation "jobs" does not exist` | Migrations haven't run | `python -m db.migrate` |
| `The database already has jobs` (seed) | Demo data only loads into an empty database | `python -m db.migrate --reset` first, if you really want the demo |
| `ModuleNotFoundError: app` | Wrong folder | `cd backend` |
| `ModuleNotFoundError: fastapi` | Virtual environment not active | Activate it (section 1) |
| Website: "Can't reach your backend" | uvicorn isn't running, the site's address isn't in `CORS_ORIGINS`, or you chose Block when the browser asked | Check the uvicorn terminal. `CORS_ORIGINS` in `.env` must include `https://ali-fathi-st.github.io` (and `http://localhost:8080` if you run the site locally). If you blocked access: click the icon left of the address bar → Site settings → allow local network / apps on this device |
| You see sample data on the published site | This browser isn't connected | Settings → Developer → Your backend → Connect |
| "This website isn't allowed to make changes" (403) | The page's address isn't in `CORS_ORIGINS` | Add it to `.env` exactly as it appears in the address bar (e.g. `http://localhost:8080`), restart uvicorn |
| `Invalid host header` (400) | You called the API by a name not in `ALLOWED_HOSTS` | Use `localhost`, or add the name to `ALLOWED_HOSTS` in `.env` |
| Most postings are "outside your area" | Your profile's locations don't match how employers write them | Add your city as employers write it ("Edmonton, AB"), and your province. Remote jobs need to say your country, or no place at all |
| A run says `robots.txt doesn't allow reading that address` | That address is off-limits to tools | Use the site's other feed address (e.g. `/feeds/...` instead of `/services/...` for the Government of Alberta) |
| A run says `not found (check the board name or company slug)` | The identifier is wrong, or that employer moved to another system | Check the careers link again (Lever slugs are case-sensitive) |
| A run says `ADZUNA_APP_ID and ADZUNA_APP_KEY aren't set` | No Adzuna keys | Add them to `.env` and restart uvicorn, or turn Adzuna off |
| Many postings quarantined | A source changed its format | `GET /api/v1/ingestion/runs` and the `quarantine` table show the reason for each |
| Collected jobs all score low | Your profile is thin | Add target titles, locations and skills; saving re-scores everything |

Looking inside the database:

```
docker compose exec db psql -U waypoint
```

Try `\dt` (tables), `\d jobs` (one table), `SELECT title, match_score FROM jobs ORDER BY match_score DESC LIMIT 10;`,
then `\q` to quit.
