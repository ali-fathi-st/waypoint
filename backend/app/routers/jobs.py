"""
The jobs endpoints. YOUR EXERCISES: steps 2b, 2c and 2d in
docs/09-backend-steps-1-2.md.

Each function already has its inputs declared (FastAPI validates them for
you) and a docstring saying exactly what it must do. Replace each
`raise HTTPException(501, ...)` with your code. `pytest tests/test_step2_jobs_api.py`
tells you what still doesn't match.

Rules for every query:
  * Never put user input into the SQL text (no f-strings with values!).
    Pass values separately:  db.execute("... WHERE id = %s", (job_id,))
    That's what makes SQL injection impossible.
  * Your SELECT must return the columns app/rows.py expects, then
    row_to_job(row) builds the response for you.
"""

from datetime import datetime

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query

from app.db import get_db
from app.rows import row_to_job
from app.schemas import Job, JobPage, JobSort, JobSource, JobStatusUpdate, ReviewFilter

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=Job)
def get_job(job_id: str, db: psycopg.Connection = Depends(get_db)) -> Job:
    """
    STEP 2b: return one job.

    - SELECT the job's columns plus its company's id, name and website
      (JOIN companies), named as app/rows.py expects.
    - If no row comes back: raise HTTPException(status_code=404, detail="Job not found")
    - Otherwise: return row_to_job(row)
    """
    raise HTTPException(status_code=501, detail="Not implemented yet: docs/09, step 2b")


@router.get("", response_model=JobPage)
def list_jobs(
    q: str | None = None,
    company: str | None = None,
    location: str | None = None,
    source: JobSource | None = None,
    found_after: datetime | None = None,
    min_score: int | None = Query(default=None, ge=0, le=100),
    review_status: ReviewFilter = "active",
    sort: JobSort = "match",
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: psycopg.Connection = Depends(get_db),
) -> JobPage:
    """
    STEP 2c: return one page of jobs, filtered and sorted.

    Filters (skip any that is None):
      q             title contains q, ignoring case
      company       company name contains it, ignoring case
      location      location contains it, ignoring case; searching "remote"
                    ALSO matches jobs whose work_arrangement is 'remote'
      source        exact match
      found_after   first_seen_at >= found_after
      min_score     match_score >= min_score
      review_status "active" = new or shortlisted (the default)
                    "all"    = no filter
                    otherwise that exact status

    Careful: in LIKE/ILIKE, % and _ are wildcards. Someone searching for "%"
    means the character, not "anything", so escape them (hint in docs/09).

    Sort:
      "match"   match_score highest first (jobs without a score last), then newest
      "newest"  first_seen_at newest first
      "posted"  posted_at newest first (no date last), then newest

    Return JobPage(items=[...], total=<count of ALL matches, not just this page>,
                   limit=limit, offset=offset)
    """
    raise HTTPException(status_code=501, detail="Not implemented yet: docs/09, step 2c")


@router.patch("/{job_id}", response_model=Job)
def update_job_status(job_id: str, body: JobStatusUpdate, db: psycopg.Connection = Depends(get_db)) -> Job:
    """
    STEP 2d: shortlist, dismiss or restore a job.

    - UPDATE the job's review_status to body.review_status.
    - If no job has that id: 404 with detail "Job not found".
    - Return the updated job (tip: reuse get_job(job_id, db)).
    """
    raise HTTPException(status_code=501, detail="Not implemented yet: docs/09, step 2d")
