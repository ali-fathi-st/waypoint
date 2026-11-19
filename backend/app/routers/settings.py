"""
Settings, your data export, and "delete everything".

Source credentials (Adzuna keys) live only in backend environment variables.
The API never returns them; it only says whether they're configured.
"""

import json
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import psycopg
from fastapi import APIRouter, Depends, Response, status
from psycopg.types.json import Jsonb

from app.config import get_settings
from app.db import get_db
from app.routers.applications import list_applications
from app.routers.candidate import read_profile
from app.routers.documents import list_documents
from app.rows import SELECT_JOB, row_to_job
from app.schemas import Settings, SettingsUpdate, SourceSettings
from app.services import storage
from app.util import invalid, utc_now

router = APIRouter(prefix="/api/v1", tags=["settings"])

# The latest run per source (DISTINCT ON picks the first row of each source).
SOURCES = """
    SELECT s.source, s.enabled, s.identifiers,
           r.started_at AS last_run_at, coalesce(r.status, 'never') AS last_run_status,
           r.fetched, r.inserted, r.updated, r.skipped, r.failed
    FROM source_settings s
    LEFT JOIN (
        SELECT DISTINCT ON (source) * FROM ingestion_runs ORDER BY source, started_at DESC
    ) r ON r.source = s.source
    ORDER BY array_position(ARRAY['greenhouse', 'lever', 'adzuna'], s.source)
"""


def credentials_configured(source: str) -> bool:
    if source == "adzuna":
        cfg = get_settings()
        return bool(cfg.adzuna_app_id and cfg.adzuna_app_key)
    return True  # Greenhouse and Lever job boards are public: no keys needed


def read_settings(db: psycopg.Connection) -> Settings:
    sources = []
    for r in db.execute(SOURCES).fetchall():
        summary = None
        if r["last_run_at"] is not None:
            summary = {k: r[k] for k in ("fetched", "inserted", "updated", "skipped", "failed")}
        sources.append(
            SourceSettings(
                source=r["source"], enabled=r["enabled"], identifiers=r["identifiers"],
                last_run_at=r["last_run_at"], last_run_status=r["last_run_status"],
                last_run_summary=summary, credentials_configured=credentials_configured(r["source"]),
            )  # fmt: skip
        )
    row = db.execute("SELECT notifications, account FROM app_settings WHERE id = 1").fetchone()
    return Settings(sources=sources, **row)


@router.get("/settings", response_model=Settings)
def get_settings_endpoint(db: psycopg.Connection = Depends(get_db)) -> Settings:
    return read_settings(db)


@router.patch("/settings", response_model=Settings)
def update_settings(body: SettingsUpdate, db: psycopg.Connection = Depends(get_db)) -> Settings:
    if body.sources is not None:
        for change in body.sources:
            identifiers = list(dict.fromkeys(i.strip() for i in change.identifiers if i.strip()))
            db.execute(
                "UPDATE source_settings SET enabled = %s, identifiers = %s WHERE source = %s",
                (change.enabled, identifiers, change.source),
            )
    if body.notifications is not None:
        db.execute("UPDATE app_settings SET notifications = %s WHERE id = 1", (Jsonb(body.notifications.model_dump()),))
    if body.account is not None:
        try:
            ZoneInfo(body.account.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise invalid("Choose a time zone from the list.", "account.timezone") from None
        db.execute("UPDATE app_settings SET account = %s WHERE id = 1", (Jsonb(body.account.model_dump()),))
    return read_settings(db)


@router.get("/export")
def export_data(db: psycopg.Connection = Depends(get_db)) -> Response:
    """Everything Waypoint holds about you, as one JSON file."""
    jobs = [row_to_job(r).model_dump(mode="json") for r in db.execute(SELECT_JOB + " ORDER BY j.first_seen_at DESC")]
    payload = {
        "exported_at": utc_now().isoformat(),
        "profile": read_profile(db).model_dump(mode="json"),
        "settings": read_settings(db).model_dump(mode="json"),
        "jobs": jobs,
        "applications": [a.model_dump(mode="json") for a in list_applications(None, None, db)],
        "documents": [d.model_dump(mode="json") for d in list_documents(None, True, db)],
    }
    return Response(
        content=json.dumps(payload, indent=2, ensure_ascii=False),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="waypoint-export-{date.today()}.json"'},
    )


@router.delete("/data", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_data(db: psycopg.Connection = Depends(get_db)) -> Response:
    """Delete every job, application, document and run, and reset the profile and settings."""
    db.execute("TRUNCATE application_events, applications, documents, jobs, companies, ingestion_runs CASCADE")
    db.execute(
        """
        UPDATE candidate_profile SET full_name = '', email = '', headline = '', summary = '',
            preferred_titles = '{}', locations = '{}', work_arrangements = '{}', salary_min = NULL,
            salary_max = NULL, salary_currency = 'CAD', exclusions = '{}', updated_at = now()
        """
    )
    for table in ("candidate_skills", "candidate_experience", "candidate_education"):
        db.execute(f"DELETE FROM {table}")  # table names are ours
    db.execute("UPDATE source_settings SET enabled = false, identifiers = '{}'")
    db.execute(
        """
        UPDATE app_settings SET
            notifications = '{"daily_digest": false, "digest_hour": 7, "digest_min_score": 70, "follow_up_reminders": true}',
            account = '{"display_name": "", "email": "", "timezone": "America/Edmonton"}'
        """
    )
    db.commit()  # the database is clean before any file is removed
    storage.delete_all()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
