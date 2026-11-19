"""
Turn database rows into API models.

row_to_job() expects a row (dict) with these keys, which is why your SELECT
must name its columns exactly like this (use AS where the name differs):

    id, source, source_job_id, title,
    company_id, company_name, company_website,
    location, work_arrangement, employment_type, description, url,
    salary_min, salary_max, salary_currency,
    posted_at, first_seen_at, last_seen_at,
    review_status, skills, match

`skills` and `match` are JSONB columns; psycopg already turns them into
Python lists and dicts.
"""

from app.schemas import CompanyRef, Job

JOB_COLUMNS = (
    "id", "source", "source_job_id", "title",
    "company_id", "company_name", "company_website",
    "location", "work_arrangement", "employment_type", "description", "url",
    "salary_min", "salary_max", "salary_currency",
    "posted_at", "first_seen_at", "last_seen_at",
    "review_status", "skills", "match",
)  # fmt: skip


def row_to_job(row: dict) -> Job:
    """Build a Job from one row. Raises a clear error if a column is missing."""
    missing = [column for column in JOB_COLUMNS if column not in row]
    if missing:
        raise KeyError(
            f"Your SELECT didn't return these columns: {', '.join(missing)}. "
            "Add them (with AS for the company ones). See app/rows.py."
        )
    return Job(
        id=row["id"],
        source=row["source"],
        source_job_id=row["source_job_id"],
        title=row["title"],
        company=CompanyRef(id=row["company_id"], name=row["company_name"], website=row["company_website"]),
        location=row["location"],
        work_arrangement=row["work_arrangement"],
        employment_type=row["employment_type"],
        description=row["description"],
        url=row["url"],
        salary_min=row["salary_min"],
        salary_max=row["salary_max"],
        salary_currency=row["salary_currency"],
        posted_at=row["posted_at"],
        first_seen_at=row["first_seen_at"],
        last_seen_at=row["last_seen_at"],
        review_status=row["review_status"],
        skills=row["skills"],
        match=row["match"],
    )
