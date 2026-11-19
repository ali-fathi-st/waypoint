"""
Applications: the six operations, with every rule from docs/06 enforced here.

  * One application per job (409 on a second one).
  * "applied" only through confirm-submission, which records that YOU
    submitted it on the employer's site. Waypoint never submits anything.
  * Only the moves in app/services/rules.py are allowed; closed stays closed.
  * Follow-ups only while applied or interviewing; cleared on any other status.
  * Every change writes an event, so the timeline is a complete history.

Each request runs in one transaction (see app/db.py), so a rule that fails
halfway leaves nothing half-written.
"""

import psycopg
from fastapi import APIRouter, Depends, Query, status
from psycopg.types.json import Jsonb

from app.db import get_db
from app.rows import SELECT_APPLICATION, rows_to_applications
from app.schemas import (
    Application,
    ApplicationCreate,
    ApplicationStatus,
    ApplicationUpdate,
    Interview,
    SubmissionConfirm,
)
from app.services.rules import (
    FOLLOW_UP_STATUSES,
    STATUS_LABEL,
    can_confirm_submission,
    can_transition,
)
from app.util import (
    account_timezone,
    conflict,
    format_date,
    invalid,
    new_id,
    not_found,
    today_in,
    utc_now,
)

router = APIRouter(prefix="/api/v1/applications", tags=["applications"])


# ---------------------------------------------------------------- helpers
def load(db: psycopg.Connection, app_id: str, lock: bool = False) -> dict:
    """The application row. FOR UPDATE stops two requests changing it at once."""
    row = db.execute(
        "SELECT * FROM applications WHERE id = %s" + (" FOR UPDATE" if lock else ""), (app_id,)
    ).fetchone()
    if row is None:
        raise not_found("Application")
    return row


def fetch(db: psycopg.Connection, app_id: str) -> Application:
    rows = db.execute(SELECT_APPLICATION + " WHERE a.id = %s", (app_id,)).fetchall()
    if not rows:
        raise not_found("Application")
    return rows_to_applications(db, rows)[0]


def add_event(db, app_id: str, event_type: str, summary: str, *, from_status=None, to_status=None, interview=None):
    """Write one timeline entry and bump updated_at."""
    now = utc_now()
    db.execute(
        """
        INSERT INTO application_events
            (id, application_id, event_type, occurred_at, summary, from_status, to_status, interview)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (new_id("evt"), app_id, event_type, now, summary, from_status, to_status,
         Jsonb(interview) if interview else None),
    )  # fmt: skip
    db.execute("UPDATE applications SET updated_at = %s WHERE id = %s", (now, app_id))


def set_status(db, app: dict, to: str, event_type: str, summary: str) -> None:
    """Change the status; clear the follow-up if it no longer makes sense."""
    clear = to not in FOLLOW_UP_STATUSES and app["follow_up_at"] is not None
    db.execute(
        "UPDATE applications SET status = %s, status_source = 'user'"
        + (", follow_up_at = NULL" if clear else "")
        + " WHERE id = %s",
        (to, app["id"]),
    )
    add_event(db, app["id"], event_type, summary, from_status=app["status"], to_status=to)
    if clear:
        add_event(
            db, app["id"], "follow_up_set",
            f"Follow-up cleared — not needed once the status is {STATUS_LABEL[to].lower()}",
        )  # fmt: skip
    app["status"] = to
    if clear:
        app["follow_up_at"] = None


def check_document(db, doc_id: str | None, document_type: str) -> dict | None:
    """A linked document must exist and be the right kind."""
    if doc_id is None:
        return None
    doc = db.execute("SELECT id, title, version, document_type FROM documents WHERE id = %s", (doc_id,)).fetchone()
    if doc is None or doc["document_type"] != document_type:
        field = "resume_document_id" if document_type == "resume" else "cover_letter_document_id"
        raise invalid("Choose a document from your list.", field)
    return doc


# ---------------------------------------------------------------- endpoints
@router.get("", response_model=list[Application])
def list_applications(
    status_filter: ApplicationStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None, max_length=200),
    db: psycopg.Connection = Depends(get_db),
) -> list[Application]:
    """Your applications, most recently changed first. q searches job title and company."""
    where, params = [], []
    if status_filter:
        where.append("a.status = %s")
        params.append(status_filter)
    if q and q.strip():
        pattern = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        where.append("(j.title ILIKE %s OR c.name ILIKE %s)")
        params += [pattern, pattern]
    sql = SELECT_APPLICATION + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY a.updated_at DESC, a.id"
    return rows_to_applications(db, db.execute(sql, params).fetchall())


@router.get("/{app_id}", response_model=Application)
def get_application(app_id: str, db: psycopg.Connection = Depends(get_db)) -> Application:
    return fetch(db, app_id)


@router.post("", response_model=Application, status_code=status.HTTP_201_CREATED)
def create_application(body: ApplicationCreate, db: psycopg.Connection = Depends(get_db)) -> Application:
    """Start tracking a job. A new job becomes shortlisted."""
    job = db.execute("SELECT id, review_status FROM jobs WHERE id = %s FOR UPDATE", (body.job_id,)).fetchone()
    if job is None:
        raise not_found("Job")
    app_id = new_id("app")
    now = utc_now()
    inserted = db.execute(
        """
        INSERT INTO applications (id, job_id, notes, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (job_id) DO NOTHING
        """,
        (app_id, job["id"], body.notes, now, now),
    ).rowcount
    if not inserted:
        raise conflict("You already have an application for this job.")
    add_event(db, app_id, "created", "Application created", to_status="saved")
    if job["review_status"] == "new":
        db.execute("UPDATE jobs SET review_status = 'shortlisted' WHERE id = %s", (job["id"],))
    return fetch(db, app_id)


@router.patch("/{app_id}", response_model=Application)
def update_application(app_id: str, body: ApplicationUpdate, db: psycopg.Connection = Depends(get_db)) -> Application:
    """Change any of: status, notes, follow_up_at, resume_document_id, cover_letter_document_id."""
    app = load(db, app_id, lock=True)
    sent = body.model_fields_set  # tells "not sent" apart from "sent as null"

    if "status" in sent and body.status is not None and body.status != app["status"]:
        if body.status == "applied":
            raise invalid("Use the confirm-submission step to mark an application as applied.")
        if not can_transition(app["status"], body.status):
            raise invalid(
                f"Can't move from {STATUS_LABEL[app['status']]} to {STATUS_LABEL[body.status]}.", "status"
            )
        set_status(db, app, body.status, "status_changed", f"Status changed to {STATUS_LABEL[body.status].lower()}")

    if "notes" in sent and body.notes is not None and body.notes != app["notes"]:
        db.execute("UPDATE applications SET notes = %s WHERE id = %s", (body.notes, app_id))
        add_event(db, app_id, "note_updated", "Notes updated")

    if "follow_up_at" in sent and body.follow_up_at != app["follow_up_at"]:
        if body.follow_up_at is not None:
            if app["status"] not in FOLLOW_UP_STATUSES:
                raise invalid("Follow-ups are only for applied or interviewing applications.", "follow_up_at")
            if app["applied_at"] and body.follow_up_at < app["applied_at"]:
                raise invalid("Follow-up must be on or after the application date.", "follow_up_at")
        db.execute("UPDATE applications SET follow_up_at = %s WHERE id = %s", (body.follow_up_at, app_id))
        add_event(
            db, app_id, "follow_up_set",
            f"Follow-up set for {format_date(body.follow_up_at)}" if body.follow_up_at else "Follow-up cleared",
        )  # fmt: skip

    for field, kind, label in (
        ("resume_document_id", "resume", "Résumé"),
        ("cover_letter_document_id", "cover_letter", "Cover letter"),
    ):
        value = getattr(body, field)
        if field in sent and value != app[field]:
            doc = check_document(db, value, kind)
            db.execute(f"UPDATE applications SET {field} = %s WHERE id = %s", (value, app_id))  # field is ours
            add_event(
                db, app_id, "document_linked",
                f'{label} set to "{doc["title"]}" (v{doc["version"]})' if doc else f"{label} removed",
            )  # fmt: skip

    return fetch(db, app_id)


@router.post("/{app_id}/confirm-submission", response_model=Application)
def confirm_submission(app_id: str, body: SubmissionConfirm, db: psycopg.Connection = Depends(get_db)) -> Application:
    """
    Record that you submitted this application yourself, on the employer's
    site. This is the only way an application becomes "applied".
    """
    app = load(db, app_id, lock=True)
    if not can_confirm_submission(app["status"]):
        raise invalid(f"This application is already {STATUS_LABEL[app['status']].lower()}.")
    if body.applied_at > today_in(account_timezone(db)):
        raise invalid("The application date can't be in the future.", "applied_at")
    if body.follow_up_at and body.follow_up_at < body.applied_at:
        raise invalid("Follow-up must be on or after the application date.", "follow_up_at")
    check_document(db, body.resume_document_id, "resume")
    check_document(db, body.cover_letter_document_id, "cover_letter")
    db.execute(
        """
        UPDATE applications
        SET resume_document_id = %s, cover_letter_document_id = %s, applied_at = %s
        WHERE id = %s
        """,
        (body.resume_document_id, body.cover_letter_document_id, body.applied_at, app_id),
    )
    set_status(
        db, app, "applied", "submission_confirmed",
        "You confirmed you submitted this application on the employer's site",
    )  # fmt: skip
    if body.follow_up_at:
        db.execute("UPDATE applications SET follow_up_at = %s WHERE id = %s", (body.follow_up_at, app_id))
        add_event(db, app_id, "follow_up_set", f"Follow-up set for {format_date(body.follow_up_at)}")
    return fetch(db, app_id)


@router.post("/{app_id}/interviews", response_model=Application)
def add_interview(app_id: str, body: Interview, db: psycopg.Connection = Depends(get_db)) -> Application:
    """Add an interview. An applied application moves to interview."""
    app = load(db, app_id, lock=True)
    if app["status"] not in ("applied", "interview"):
        raise invalid("Interviews can be added once an application is applied.")
    if app["status"] == "applied":
        set_status(db, app, "interview", "status_changed", "Status changed to interview")
    label = "On-site" if body.format == "onsite" else body.format.capitalize()
    add_event(
        db, app_id, "interview_scheduled", f"{label} interview scheduled",
        interview=body.model_dump(mode="json"),
    )  # fmt: skip
    return fetch(db, app_id)

