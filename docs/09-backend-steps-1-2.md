# 9. Backend steps 1 and 2: your first API

By the end of this guide the Jobs page on your computer shows jobs from
**your** PostgreSQL database, through **your** FastAPI code, and shortlisting
a job saves to the database.

**How this works:** the plumbing is already done (settings, connections, the
migration runner, the seed script, response models, CORS). The parts that
teach you the most are left for you:

| Step | You write | File | Checked by |
| --- | --- | --- | --- |
| 1 | Nothing: just get it running | | `tests/test_step1_health.py` |
| 2a | The tables, in SQL | `db/migrations/001_create_jobs.sql` | `tests/test_step2a_schema.py` |
| 2b | Get one job | `app/routers/jobs.py` | `tests/test_step2_jobs_api.py -k get` |
| 2c | List, filter, sort, page | `app/routers/jobs.py` | `tests/test_step2_jobs_api.py` |
| 2d | Shortlist / dismiss | `app/routers/jobs.py` | `tests/test_step2_jobs_api.py -k update` |
| 3 | Point the website at it | `frontend/js/config.js` | Your eyes |

The tests are the definition of done. When they pass, you're done; read a
failing test's name and message before anything else.

Commands are shown for **Windows (PowerShell)** and **Mac**. Run everything
from the `backend` folder unless it says otherwise.

---

## Before you start

You need:

- **Docker Desktop**, running (the whale icon is steady, not animating).
- **Python 3.12 or newer.** Check: `py --version` (Windows) or `python3 --version` (Mac).
- **This branch** of the repository:
  ```
  git fetch
  git switch backend-steps-1-2
  ```
  (If it has already been merged, just `git switch main` and `git pull`.)

---

## Step 1: get the API running

### 1.1 Start PostgreSQL

```
cd backend
docker compose up -d
docker compose ps
```

`ps` should show the `db` service as **healthy** after a few seconds. The first
start also creates a second database, `waypoint_test`, which the tests use, so
running the tests never touches your real data.

### 1.2 Make a virtual environment and install

A virtual environment keeps this project's packages separate from everything
else on your computer.

**Windows**
```
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
```

If PowerShell says running scripts is disabled, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then try again.

**Mac**
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Your prompt now starts with `(.venv)`. Each time you open a new terminal,
activate it again (the second line above).

`.env` holds your settings. It is listed in `.gitignore`, so it never goes to
GitHub. The values in it only work on your computer, which is the point.

### 1.3 Run it

```
uvicorn app.main:app --reload
```

Open these in your browser:

- http://localhost:8000/health shows `{"status":"ok"}`
- http://localhost:8000/docs is FastAPI's interactive page. You'll see the
  three jobs endpoints; trying them now returns **501 Not implemented yet**.
  That's your work for step 2.

`--reload` restarts the server whenever you save a Python file. Leave it
running in this terminal and open a second one (activate the venv there too)
for everything else.

### 1.4 Check

```
pytest tests/test_step1_health.py
```

Four tests pass. If you now run plain `pytest`, it stops with
**"001_create_jobs.sql has no SQL yet"**. That's expected; on to step 2a.

<details>
<summary>What each backend file does</summary>

| File | Job |
| --- | --- |
| `app/main.py` | Creates the app, sets CORS, adds the routers |
| `app/config.py` | Reads `.env` into a `Settings` object |
| `app/db.py` | `get_db()` gives each request its own database connection, committed at the end |
| `app/schemas.py` | The exact JSON shapes the website expects (from [06](06-api-contract.md)) |
| `app/rows.py` | `row_to_job(row)` turns a database row into a `Job` |
| `app/routers/jobs.py` | **Yours:** the jobs endpoints |
| `db/migrations/*.sql` | **Yours:** the database tables, in plain SQL |
| `db/migrate.py` | Applies each migration file once, in order |
| `db/seed.py` + `db/seed/jobs.json` | Loads the same fictional jobs the website uses in sample mode |
| `tests/` | The checks, one file per step |

</details>

---

## Step 2a: create the tables (SQL)

Open `db/migrations/001_create_jobs.sql`. The comment block is the spec:
every column, its type, whether it's required, the allowed values, and the
rules. Write two `CREATE TABLE` statements and three `CREATE INDEX` statements
under it.

Then:

```
python -m db.migrate
python -m db.seed
pytest tests/test_step2a_schema.py
```

`db.seed` should say **Inserted 22 jobs**.

**Made a mistake after migrating?** A migration runs only once, so editing the
file changes nothing until you start over. While you're learning, that's fine:

```
python -m db.migrate --reset
python -m db.seed
```

`--reset` deletes everything in the development database. (The tests reset
the test database themselves, every time.) Once a project has real data, you
never edit an applied migration; you add `002_...sql` instead.

**Look at your data** in PostgreSQL's own shell:

```
docker compose exec db psql -U waypoint
```

Try `\dt` (list tables), `\d jobs` (describe), `SELECT id, title, review_status FROM jobs LIMIT 5;`,
then `\q` to quit.

<details>
<summary>Hint 1: the shape of a CREATE TABLE</summary>

```sql
CREATE TABLE things (
    id      text PRIMARY KEY,
    name    text NOT NULL,
    note    text,                     -- no NOT NULL = optional
    owner   text NOT NULL REFERENCES people (id),
    created timestamptz NOT NULL DEFAULT now()
);
```

Create `companies` first: `jobs` points at it, and you can't reference a
table that doesn't exist yet.

</details>

<details>
<summary>Hint 2: allowed values, ranges, and rules across columns</summary>

A `CHECK` keeps bad values out, whoever writes them:

```sql
colour  text NOT NULL CHECK (colour IN ('red', 'green')),
age     integer CHECK (age BETWEEN 0 AND 150),
```

A rule about two columns, or uniqueness across two columns, goes after the
last column, separated by commas:

```sql
    ...,
    UNIQUE (a, b),
    CHECK (high >= low)
);
```

A `CHECK` that compares to NULL passes, so optional salaries still work.

</details>

<details>
<summary>Hint 3: JSONB defaults and indexes</summary>

```sql
tags jsonb NOT NULL DEFAULT '[]',
```

```sql
CREATE INDEX things_created_idx ON things (created DESC);
```

</details>

<details>
<summary>Why these choices?</summary>

- **text with CHECK instead of ENUM:** adding a value later is a one-line
  change, and the error message names the rule.
- **UNIQUE (source, source_job_id):** when real job collection starts (step
  6), the same posting comes back every day. The database itself refuses the
  duplicate, so no bug in Python can create one.
- **match_score as its own column** even though `match` holds the score too:
  you can't index inside JSON cheaply, and sorting by score is the most common
  query.
- **timestamptz:** always stores the exact moment; never ambiguous about time
  zones.

</details>

---

## Step 2b: get one job

In `app/routers/jobs.py`, replace the `raise` in `get_job` with your code. The
docstring says what it must do.

```
pytest tests/test_step2_jobs_api.py -k "get or field or location_comes or test_unknown_job"
```

Then try it at http://localhost:8000/docs → **GET /api/v1/jobs/{job_id}** →
*Try it out* → `job_001`.

<details>
<summary>Hint 1: running a query with psycopg</summary>

```python
row = db.execute("SELECT name FROM companies WHERE id = %s", (company_id,)).fetchone()
# row is a dict, or None if nothing matched
```

The `%s` is a placeholder; the value travels separately, so it can never
change the meaning of the SQL. Note the comma in `(company_id,)`: it must be
a tuple.

</details>

<details>
<summary>Hint 2: the company columns</summary>

The job's company lives in another table, so you need a `JOIN`, and you need
to rename columns so they match what `row_to_job` expects:

```sql
SELECT j.id, j.title, ..., c.name AS company_name, c.website AS company_website
FROM jobs j
JOIN companies c ON c.id = j.company_id
WHERE j.id = %s
```

Put the `SELECT ... JOIN` part in a constant at the top of the file. You'll
reuse it in 2c.

</details>

---

## Step 2c: list, filter, sort and page

The biggest step. Do it in pieces and run the tests after each one:

1. No filters: all active jobs, sorted by match, with `LIMIT` and `OFFSET`.
   Also count them for `total`.
2. `review_status`.
3. The text filters: `q`, `company`, `location`.
4. `source`, `found_after`, `min_score`.
5. The other two sorts.

```
pytest tests/test_step2_jobs_api.py -k "not update"
```

<details>
<summary>Hint 1: building a WHERE clause from optional filters</summary>

Collect the conditions and their values in two lists, side by side:

```python
where, params = [], []
if source:
    where.append("j.source = %s")
    params.append(source)
# ... one block per filter
where_sql = " WHERE " + " AND ".join(where) if where else ""
```

Then the same `where_sql` and `params` go into both queries: the `count(*)`
for `total` and the `SELECT` for the page.

</details>

<details>
<summary>Hint 2: case-insensitive "contains"</summary>

PostgreSQL's `ILIKE` ignores case, and `%` means "anything":

```python
where.append("j.title ILIKE %s")
params.append(f"%{q}%")
```

The `%` signs go in the **value**, never in the SQL text.

</details>

<details>
<summary>Hint 3: when the user searches for % or _</summary>

In `ILIKE`, `%` and `_` are wildcards, so a search for `%` would match every
job. Put a backslash in front of each (and in front of backslashes) before
wrapping in `%...%`:

```python
def like_pattern(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
```

</details>

<details>
<summary>Hint 4: sorting without SQL injection</summary>

`ORDER BY` can't use `%s`. But `sort` can only be one of three values
(FastAPI already rejected anything else), so map each to a fixed piece of SQL
you wrote yourself:

```python
ORDER_BY = {
    "match": "...",
    "newest": "...",
    "posted": "...",
}
sql = SELECT_JOB + where_sql + f" ORDER BY {ORDER_BY[sort]} LIMIT %s OFFSET %s"
```

That f-string is safe because the inserted text is yours, not the user's.
For "no score last", look up `NULLS LAST`.

</details>

---

## Step 2d: shortlist and dismiss

```
pytest tests/test_step2_jobs_api.py -k update
```

<details>
<summary>Hint: did the UPDATE find the job?</summary>

`db.execute(...)` returns a cursor, and `cursor.rowcount` says how many rows
changed. Zero means no job has that id.

You don't need to call `commit()`: `get_db()` commits when the request
succeeds.

</details>

Now run everything:

```
pytest
```

All tests pass? Steps 1 and 2 are done.

---

## Step 3: show it on the website

1. Keep `uvicorn` running.
2. In a **new** terminal, from the **repository** folder (not `backend`),
   serve the site:
   ```
   py -m http.server 8080 --directory frontend        # Windows
   python3 -m http.server 8080 --directory frontend   # Mac
   ```
3. Edit `frontend/js/config.js`:
   ```js
   export const config = {
     apiMode: "hybrid",
     apiBaseUrl: "http://localhost:8000",
     liveOperations: ["listJobs", "getJob", "updateJobStatus"],
   };
   ```
4. Open http://localhost:8080/jobs.html. The sidebar says **Hybrid**. Search,
   filter, open a job, shortlist it; watch the requests appear in the
   `uvicorn` terminal. Check in `psql` that `review_status` changed.

**Don't commit this `config.js` change.** GitHub Pages can't reach
`localhost:8000`, so the published site would show errors. Undo it before you
commit: `git restore frontend/js/config.js`.

Everything not in `liveOperations` (applications, documents, the dashboard)
still uses sample data. Those move over in later steps.

---

## When something goes wrong

| You see | Why | Fix |
| --- | --- | --- |
| `Can't reach the test database` | PostgreSQL isn't running | `docker compose up -d`, wait for **healthy** |
| `port is already allocated` (Docker) | Another PostgreSQL uses port 5432 | Stop it, or change `"5432:5432"` to `"5433:5432"` and use `5433` in `.env` |
| `database "waypoint_test" does not exist` | The volume was made before the init script existed | `docker compose down -v`, then `docker compose up -d` (deletes your dev data) |
| `has no SQL yet` | Step 2a isn't written | Write the SQL |
| `The sample data didn't load` | A column name or type doesn't match the spec | Compare your SQL with the comment block, then `--reset` |
| `relation "jobs" does not exist` | Migrations haven't run on this database | `python -m db.migrate` |
| `Your SELECT didn't return these columns` | A column is missing or not renamed with `AS` | Add it; see `app/rows.py` |
| `ModuleNotFoundError: app` | Running from the wrong folder | `cd backend` |
| `ModuleNotFoundError: fastapi` | The virtual environment isn't active | Activate it (step 1.2) |
| `501 Not implemented yet` | That endpoint is still a stub | Write it |
| Website says it can't reach the server | `uvicorn` stopped, or CORS | Check the `uvicorn` terminal; the site must be on `http://localhost:8080` (listed in `CORS_ORIGINS`) |
| `ValidationError` in the `uvicorn` terminal | A value from the database doesn't fit `app/schemas.py` | The message names the field |

Stuck after the hints? Ask Claude to **review** your code rather than write
it: paste the function and the failing test's output.

## What you practised

- Designing a table from a spec: types, NULL, defaults, keys, constraints, indexes.
- Letting the database enforce rules (duplicates, allowed values).
- Parameterised queries, the habit that prevents SQL injection.
- Building dynamic filters safely.
- Pagination with a total count.
- Testing against a throwaway database.

Next: **step 3, profile and scoring** (see [backend/README.md](../backend/README.md#build-order)).
