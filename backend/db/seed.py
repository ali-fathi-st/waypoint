"""
Load the FICTIONAL demo data: the same companies, jobs, applications,
documents, profile and settings the website shows in sample mode.

    python -m db.seed           into DATABASE_URL
    python -m db.seed --test    into TEST_DATABASE_URL

For development and demos only. Every company and person in db/seed/demo.json
is made up and every link points to example.com, so never load it into the
database you use for your real job search.

Dates are moved forward by whole days so the newest job always arrived today.
It only runs on an empty database (start over with: python -m db.migrate --reset).
"""

import argparse
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg
from psycopg.types.json import Jsonb

from app.config import get_settings

SEED_FILE = Path(__file__).parent / "seed" / "demo.json"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def shift_dates(value, days: int):
    """Move every date and timestamp in the data forward by `days`."""
    if isinstance(value, dict):
        return {k: shift_dates(v, days) for k, v in value.items()}
    if isinstance(value, list):
        return [shift_dates(v, days) for v in value]
    if isinstance(value, str):
        if DATETIME.match(value):
            return (_parse(value) + timedelta(days=days)).isoformat()
        if DATE.match(value):
            return (date.fromisoformat(value) + timedelta(days=days)).isoformat()
    return value


def load_demo() -> dict:
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    tz = ZoneInfo(data["timezone"])
    generated = _parse(data["generated_at"]).astimezone(tz).date()
    days = (datetime.now(tz).date() - generated).days
    return shift_dates(data, days)


def seed(database_url: str) -> int:
    """Insert the demo data. Returns the number of jobs inserted."""
    d = load_demo()
    with psycopg.connect(database_url) as conn:
        if conn.execute("SELECT 1 FROM jobs LIMIT 1").fetchone():
            raise SystemExit("The database already has jobs. Start over with: python -m db.migrate --reset")

        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO companies (id, name, website) VALUES (%s, %s, %s)",
                [(c["id"], c["name"], c["website"]) for c in d["companies"]],
            )
            cur.executemany(
                """
                INSERT INTO jobs (id, source, source_job_id, title, company_id, location, work_arrangement,
                    employment_type, description, url, salary_min, salary_max, salary_currency, posted_at,
                    first_seen_at, last_seen_at, review_status, skills, match, match_score)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (j["id"], j["source"], j["source_job_id"], j["title"], j["company"]["id"], j["location"],
                     j["work_arrangement"], j["employment_type"], j["description"], j["url"], j["salary_min"],
                     j["salary_max"], j["salary_currency"], j["posted_at"], j["first_seen_at"], j["last_seen_at"],
                     j["review_status"], Jsonb(j["skills"]), Jsonb(j["match"]) if j["match"] else None,
                     j["match"]["score"] if j["match"] else None)
                    for j in d["jobs"]
                ],
            )  # fmt: skip

            p = d["profile"]
            cur.execute(
                """
                UPDATE candidate_profile SET full_name = %s, email = %s, headline = %s, summary = %s,
                    preferred_titles = %s, locations = %s, work_arrangements = %s, salary_min = %s,
                    salary_max = %s, salary_currency = %s, exclusions = %s, updated_at = %s
                WHERE id = 'me'
                """,
                (p["full_name"], p["email"], p["headline"], p["summary"], p["preferred_titles"], p["locations"],
                 p["work_arrangements"], p["salary_min"], p["salary_max"], p["salary_currency"], p["exclusions"],
                 p["updated_at"]),
            )  # fmt: skip
            cur.executemany(
                "INSERT INTO candidate_skills (profile_id, position, name, proficiency, years) VALUES ('me', %s, %s, %s, %s)",
                [(i, s["name"], s["proficiency"], s["years"]) for i, s in enumerate(p["skills"])],
            )
            cur.executemany(
                "INSERT INTO candidate_experience (id, profile_id, position, title, company, start_month, end_month, "
                "description) VALUES (%s, 'me', %s, %s, %s, %s, %s, %s)",
                [(e["id"], i, e["title"], e["company"], e["start_month"], e["end_month"], e["description"])
                 for i, e in enumerate(p["experience"])],
            )  # fmt: skip
            cur.executemany(
                "INSERT INTO candidate_education (id, profile_id, position, institution, credential, field, end_month, "
                "in_progress) VALUES (%s, 'me', %s, %s, %s, %s, %s, %s)",
                [(e["id"], i, e["institution"], e["credential"], e["field"], e["end_month"], e["in_progress"])
                 for i, e in enumerate(p["education"])],
            )  # fmt: skip

            cur.executemany(
                """
                INSERT INTO documents (id, document_type, title, version, status, origin, related_job_id,
                    file_name, size_bytes, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [(x["id"], x["document_type"], x["title"], x["version"], x["status"], x["origin"],
                  x["related_job_id"], x["file_name"], x["size_bytes"], x["created_at"], x["updated_at"])
                 for x in d["documents"]],
            )  # fmt: skip

            cur.executemany(
                """
                INSERT INTO applications (id, job_id, status, status_source, applied_at, follow_up_at,
                    resume_document_id, cover_letter_document_id, notes, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [(a["id"], a["job_id"], a["status"], a["status_source"], a["applied_at"], a["follow_up_at"],
                  a["resume_document_id"], a["cover_letter_document_id"], a["notes"], a["created_at"],
                  a["updated_at"]) for a in d["applications"]],
            )  # fmt: skip
            cur.executemany(
                """
                INSERT INTO application_events (id, application_id, event_type, occurred_at, summary,
                    from_status, to_status, interview)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [(e["id"], e["application_id"], e["event_type"], e["occurred_at"], e["summary"], e["from_status"],
                  e["to_status"], Jsonb(e["interview"]) if e["interview"] else None)
                 for a in d["applications"] for e in a["events"]],
            )  # fmt: skip

            s = d["settings"]
            for src in s["sources"]:
                cur.execute(
                    "UPDATE source_settings SET enabled = %s, identifiers = %s WHERE source = %s",
                    (src["enabled"], src["identifiers"], src["source"]),
                )
                if src["last_run_at"]:
                    r = src["last_run_summary"]
                    cur.execute(
                        """
                        INSERT INTO ingestion_runs (source, started_at, finished_at, status,
                            fetched, inserted, updated, skipped, failed)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (src["source"], src["last_run_at"], src["last_run_at"], src["last_run_status"],
                         r["fetched"], r["inserted"], r["updated"], r["skipped"], r["failed"]),
                    )  # fmt: skip
            cur.execute(
                "UPDATE app_settings SET notifications = %s, account = %s WHERE id = 1",
                (Jsonb(s["notifications"]), Jsonb(s["account"])),
            )
    return len(d["jobs"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--test", action="store_true", help="use TEST_DATABASE_URL")
    args = parser.parse_args()
    settings = get_settings()
    try:
        count = seed(settings.test_database_url if args.test else settings.database_url)
    except psycopg.errors.UndefinedTable as error:
        raise SystemExit(f"{error}\nCreate the tables first: python -m db.migrate") from error
    print(f"Loaded the fictional demo data: {count} jobs, plus applications, documents, profile and settings.")


if __name__ == "__main__":
    main()
