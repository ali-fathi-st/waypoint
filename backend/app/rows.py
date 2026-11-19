"""
Turn database rows into API models, and the SELECTs that produce those rows.

Each SELECT names its columns exactly as the model's fields (using AS where
the name differs), so building the model is just a matter of passing them on.
"""

from app.schemas import (
    Application,
    ApplicationEvent,
    ApplicationJob,
    CompanyRef,
    Document,
    Job,
)

# One job, with its company and its application (if you have one).
SELECT_JOB = """
    SELECT j.id, j.source, j.source_job_id, j.title,
           c.id AS company_id, c.name AS company_name, c.website AS company_website,
           j.location, j.work_arrangement, j.employment_type, j.description, j.url,
           j.salary_min, j.salary_max, j.salary_currency,
           j.posted_at, j.first_seen_at, j.last_seen_at,
           j.review_status, j.skills, j.match,
           a.id AS application_id
    FROM jobs j
    JOIN companies c ON c.id = j.company_id
    LEFT JOIN applications a ON a.job_id = j.id
"""

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
        raise KeyError(f"The SELECT didn't return these columns: {', '.join(missing)}. See app/rows.py.")
    fields = {k: row[k] for k in JOB_COLUMNS if not k.startswith("company_")}
    return Job(
        **fields,
        company=CompanyRef(id=row["company_id"], name=row["company_name"], website=row["company_website"]),
        application_id=row.get("application_id"),
    )


SELECT_APPLICATION = """
    SELECT a.id, a.job_id, a.status, a.status_source, a.applied_at, a.follow_up_at,
           a.resume_document_id, a.cover_letter_document_id, a.notes, a.created_at, a.updated_at,
           j.title AS job_title, c.name AS job_company_name, j.location AS job_location,
           j.url AS job_url, j.source AS job_source
    FROM applications a
    JOIN jobs j ON j.id = a.job_id
    JOIN companies c ON c.id = j.company_id
"""

SELECT_EVENTS = """
    SELECT id, application_id, event_type, occurred_at, summary, from_status, to_status, interview
    FROM application_events
    WHERE application_id = ANY(%s)
    ORDER BY occurred_at DESC, id DESC
"""


def rows_to_applications(db, rows: list[dict]) -> list[Application]:
    """Build Applications, fetching all their events in one query."""
    events: dict[str, list[ApplicationEvent]] = {row["id"]: [] for row in rows}
    if rows:
        for event in db.execute(SELECT_EVENTS, (list(events),)).fetchall():
            events[event["application_id"]].append(ApplicationEvent(**event))
    return [
        Application(
            **{k: v for k, v in row.items() if not k.startswith("job_") or k == "job_id"},
            job=ApplicationJob(
                title=row["job_title"],
                company_name=row["job_company_name"],
                location=row["job_location"],
                url=row["job_url"],
                source=row["job_source"],
            ),
            events=events[row["id"]],
        )
        for row in rows
    ]


SELECT_DOCUMENT = """
    SELECT d.id, d.document_type, d.title, d.version, d.status, d.origin,
           d.related_job_id, j.title AS related_job_title,
           d.file_name, d.size_bytes, d.created_at, d.updated_at
    FROM documents d
    LEFT JOIN jobs j ON j.id = d.related_job_id
"""


def row_to_document(row: dict) -> Document:
    return Document(**row)
