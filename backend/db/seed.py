"""
Load the fictional sample jobs into the database.

    python -m db.seed           into DATABASE_URL
    python -m db.seed --test    into TEST_DATABASE_URL

The data in db/seed/jobs.json is the same fictional data the website uses in
sample mode (every company is made up; every link points to example.com).
Dates are shifted so the newest job always looks like it arrived today.

Running it again is safe: existing rows are left alone (ON CONFLICT DO NOTHING).
This script expects the tables from db/migrations/001_create_jobs.sql.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from app.config import get_settings

SEED_FILE = Path(__file__).parent / "seed" / "jobs.json"


def _parse(value: str) -> datetime:
    """Read an ISO timestamp like 2026-11-14T12:16:00.000Z."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _shift(value: str | None, offset) -> datetime | None:
    """Move a timestamp forward so the sample data stays recent."""
    return None if value is None else _parse(value) + offset


def seed(database_url: str) -> int:
    """Insert companies and jobs. Returns the number of jobs inserted."""
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    offset = datetime.now(timezone.utc) - _parse(data["generated_at"])
    inserted = 0
    with psycopg.connect(database_url) as conn:
        for company in data["companies"]:
            conn.execute(
                "INSERT INTO companies (id, name, website) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
                (company["id"], company["name"], company["website"]),
            )
        for job in data["jobs"]:
            match = job["match"]
            if match:
                match = {**match, "computed_at": _shift(match["computed_at"], offset).isoformat()}
            cursor = conn.execute(
                """
                INSERT INTO jobs (
                    id, source, source_job_id, title, company_id, location,
                    work_arrangement, employment_type, description, url,
                    salary_min, salary_max, salary_currency,
                    posted_at, first_seen_at, last_seen_at,
                    review_status, skills, match, match_score
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    job["id"], job["source"], job["source_job_id"], job["title"], job["company"]["id"],
                    job["location"], job["work_arrangement"], job["employment_type"], job["description"],
                    job["url"], job["salary_min"], job["salary_max"], job["salary_currency"],
                    _shift(job["posted_at"], offset), _shift(job["first_seen_at"], offset),
                    _shift(job["last_seen_at"], offset), job["review_status"], Jsonb(job["skills"]),
                    Jsonb(match) if match else None, match["score"] if match else None,
                ),  # fmt: skip
            )
            inserted += cursor.rowcount
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--test", action="store_true", help="use TEST_DATABASE_URL")
    args = parser.parse_args()
    settings = get_settings()
    try:
        count = seed(settings.test_database_url if args.test else settings.database_url)
    except psycopg.errors.UndefinedTable as error:
        raise SystemExit(f"{error}\nCreate the tables first: python -m db.migrate") from error
    print(f"Inserted {count} jobs (existing ones were kept).")


if __name__ == "__main__":
    main()
