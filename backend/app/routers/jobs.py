"""
The jobs endpoints: list (with filters, sorting and pages), get one, and
shortlist / dismiss.

Every value from the user goes to PostgreSQL as a separate parameter (%s),
never pasted into the SQL text, so SQL injection is impossible. The one
f-string below inserts ORDER BY text chosen from a fixed dictionary, never
user input.
"""

from datetime import datetime

import psycopg
from fastapi import APIRouter, Depends, Query

from app.db import get_db
from app.rows import SELECT_JOB, row_to_job
from app.schemas import Job, JobPage, JobSort, JobSource, JobStatusUpdate, ReviewFilter
from app.util import not_found

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

# Ending with j.id makes the order fully predictable, so pages never overlap.
ORDER_BY = {
    "match": "j.match_score DESC NULLS LAST, j.first_seen_at DESC, j.id",
    "newest": "j.first_seen_at DESC, j.id",
    "posted": "j.posted_at DESC NULLS LAST, j.first_seen_at DESC, j.id",
}


def _like(text: str) -> str:
    """'data' -> '%data%', with ILIKE's wildcards escaped."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


@router.get("/{job_id}", response_model=Job)
def get_job(job_id: str, db: psycopg.Connection = Depends(get_db)) -> Job:
    """One job, or 404."""
    row = db.execute(SELECT_JOB + " WHERE j.id = %s", (job_id,)).fetchone()
    if row is None:
        raise not_found("Job")
    return row_to_job(row)


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
    One page of jobs. Filters that are None are skipped; text filters ignore
    case; location "remote" also matches remote jobs with no location.
    review_status "active" (the default) means new or shortlisted.
    `total` counts every match, not just this page.

    % and _ are wildcards in ILIKE, so they're escaped: searching "%" finds a
    literal percent sign, not everything.
    """
    where, params = [], []
    if q:
        where.append("j.title ILIKE %s")
        params.append(_like(q))
    if company:
        where.append("c.name ILIKE %s")
        params.append(_like(company))
    if location:
        if location.strip().lower() == "remote":
            where.append("(j.location ILIKE %s OR j.work_arrangement = 'remote')")
        else:
            where.append("j.location ILIKE %s")
        params.append(_like(location.strip()))
    if source:
        where.append("j.source = %s")
        params.append(source)
    if found_after:
        where.append("j.first_seen_at >= %s")
        params.append(found_after)
    if min_score is not None:
        where.append("j.match_score >= %s")
        params.append(min_score)
    if review_status == "active":
        where.append("j.review_status IN ('new', 'shortlisted')")
    elif review_status != "all":
        where.append("j.review_status = %s")
        params.append(review_status)
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    total = db.execute(
        "SELECT count(*) AS n FROM jobs j JOIN companies c ON c.id = j.company_id" + where_sql, params
    ).fetchone()["n"]
    rows = db.execute(
        SELECT_JOB + where_sql + f" ORDER BY {ORDER_BY[sort]} LIMIT %s OFFSET %s", [*params, limit, offset]
    ).fetchall()
    return JobPage(items=[row_to_job(r) for r in rows], total=total, limit=limit, offset=offset)


@router.patch("/{job_id}", response_model=Job)
def update_job_status(job_id: str, body: JobStatusUpdate, db: psycopg.Connection = Depends(get_db)) -> Job:
    """Shortlist, dismiss or restore a job."""
    cur = db.execute("UPDATE jobs SET review_status = %s WHERE id = %s", (body.review_status, job_id))
    if cur.rowcount == 0:
        raise not_found("Job")
    return get_job(job_id, db)
