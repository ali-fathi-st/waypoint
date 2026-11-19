"""
Collect jobs from every enabled source: one run per source, logged in
ingestion_runs (Settings > Sources shows the latest).

    python -m app.ingestion.run                  all enabled sources
    python -m app.ingestion.run --source lever   just one (even if disabled)

Run it on a schedule (cron, Windows Task Scheduler) to collect daily; see
docs/09-backend.md.

For each posting:
  1. Save it as-is in raw_postings (what the source actually said).
  2. Normalize it. If it's unusable, it goes to quarantine with the reason.
  3. Already stored (same source + id)?   unchanged -> skipped, changed -> updated
  4. Same job from another source?        skipped (cross-source duplicate)
  5. Otherwise                            inserted, skills found, scored
Your review status and applications are never touched by a run.

Nothing is invented: if a source fails, the run says so and no jobs appear.
"""

import argparse
import hashlib
import json
import logging
from dataclasses import asdict

import psycopg
from psycopg.types.json import Jsonb

from app.config import get_settings
from app.db import connect
from app.ingestion.skills import extract_skills
from app.ingestion.sources import ADAPTERS
from app.ingestion.sources.base import Http, Invalid, Posting, SourceError
from app.ingestion.text import norm, slug
from app.services.matching import rescore
from app.util import new_id, utc_now

log = logging.getLogger("waypoint.ingestion")
RAW_RETENTION_DAYS = 30


def content_hash(p: Posting) -> str:
    """Fingerprint of the fields that matter. A new fingerprint means the posting really changed."""
    fields = asdict(p)
    fields["posted_at"] = p.posted_at.isoformat() if p.posted_at else None
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def dedupe_key(p: Posting) -> str:
    """Company + title + city, normalized: the same job posted on two boards gets the same key."""
    city = "remote" if p.work_arrangement == "remote" else norm((p.location or "").split(",")[0])
    return f"{norm(p.company_name)}|{norm(p.title)}|{city}"


def ensure_company(db, p: Posting) -> str:
    company_id = f"co_{slug(p.company_name)}"
    db.execute(
        "INSERT INTO companies (id, name, website) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING",
        (company_id, p.company_name.strip(), p.company_website),
    )
    return company_id


def store(db, source: str, p: Posting, vocabulary: list[str]) -> tuple[str, str | None]:
    """Insert or update one posting. Returns (outcome, job id)."""
    now = utc_now()
    digest, key = content_hash(p), dedupe_key(p)
    existing = db.execute(
        "SELECT id, content_hash FROM jobs WHERE source = %s AND source_job_id = %s", (source, p.source_job_id)
    ).fetchone()
    if existing:
        if existing["content_hash"] == digest:
            db.execute("UPDATE jobs SET last_seen_at = %s WHERE id = %s", (now, existing["id"]))
            return "skipped", None
        db.execute(
            """
            UPDATE jobs SET title = %s, company_id = %s, location = %s, work_arrangement = %s,
                employment_type = %s, description = %s, url = %s, salary_min = %s, salary_max = %s,
                salary_currency = %s, posted_at = %s, skills = %s, last_seen_at = %s,
                content_hash = %s, dedupe_key = %s
            WHERE id = %s
            """,
            (p.title, ensure_company(db, p), p.location, p.work_arrangement, p.employment_type, p.description,
             p.url, p.salary_min, p.salary_max, p.salary_currency, p.posted_at,
             Jsonb(extract_skills(p.description, vocabulary)), now, digest, key, existing["id"]),
        )  # fmt: skip
        return "updated", existing["id"]

    duplicate = db.execute(
        "SELECT id FROM jobs WHERE dedupe_key = %s AND source <> %s LIMIT 1", (key, source)
    ).fetchone()
    if duplicate:
        db.execute("UPDATE jobs SET last_seen_at = %s WHERE id = %s", (now, duplicate["id"]))
        return "skipped", None

    job_id = new_id("job")
    db.execute(
        """
        INSERT INTO jobs (id, source, source_job_id, title, company_id, location, work_arrangement,
            employment_type, description, url, salary_min, salary_max, salary_currency, posted_at,
            first_seen_at, last_seen_at, review_status, skills, content_hash, dedupe_key)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'new', %s, %s, %s)
        """,
        (job_id, source, p.source_job_id, p.title, ensure_company(db, p), p.location, p.work_arrangement,
         p.employment_type, p.description, p.url, p.salary_min, p.salary_max, p.salary_currency, p.posted_at,
         now, now, Jsonb(extract_skills(p.description, vocabulary)), digest, key),
    )  # fmt: skip
    return "inserted", job_id


def run_source(source: str, database_url: str | None = None, http: Http | None = None) -> dict:
    """Collect one source. Returns the run row (status and counts)."""
    adapter = ADAPTERS[source]
    own_http = http is None
    http = http or Http(timeout=get_settings().http_timeout)
    counts = {"fetched": 0, "inserted": 0, "updated": 0, "skipped": 0, "failed": 0}
    errors: list[dict] = []
    with connect(database_url) as db:
        settings = db.execute("SELECT identifiers FROM source_settings WHERE source = %s", (source,)).fetchone()
        profile = db.execute("SELECT locations FROM candidate_profile LIMIT 1").fetchone()
        vocabulary = [r["name"] for r in db.execute("SELECT name FROM candidate_skills ORDER BY position")]
        run_id = db.execute(
            "INSERT INTO ingestion_runs (source) VALUES (%s) RETURNING id", (source,)
        ).fetchone()["id"]
        db.commit()  # the run shows as "running" straight away

        identifiers = settings["identifiers"] if settings else []
        ok_identifiers = 0
        for identifier in identifiers:
            context = {"locations": profile["locations"] if profile else []}
            try:
                raws = adapter.fetch(http, identifier, context)
            except (SourceError, Invalid) as error:
                errors.append({"identifier": identifier, "error": str(error)})
                log.warning("%s/%s: %s", source, identifier, error)
                continue
            ok_identifiers += 1
            touched: list[str] = []
            for raw in raws:
                counts["fetched"] += 1
                raw_id = str(raw.get("id", "")) if isinstance(raw, dict) else None
                db.execute(
                    "INSERT INTO raw_postings (run_id, source, identifier, source_job_id, payload) VALUES (%s, %s, %s, %s, %s)",
                    (run_id, source, identifier, raw_id, Jsonb(raw)),
                )
                try:
                    posting = adapter.normalize(raw, identifier, context)
                    with db.transaction():  # one bad row can't undo the others
                        outcome, job_id = store(db, source, posting, vocabulary)
                except (Invalid, KeyError, TypeError, ValueError, psycopg.DataError, psycopg.IntegrityError) as error:
                    counts["failed"] += 1
                    db.execute(
                        "INSERT INTO quarantine (run_id, source, source_job_id, payload, reason) VALUES (%s, %s, %s, %s, %s)",
                        (run_id, source, raw_id, Jsonb(raw), f"{error.__class__.__name__}: {error}"[:500]),
                    )
                    continue
                counts[outcome] += 1
                if job_id:
                    touched.append(job_id)
            if touched:
                rescore(db, touched)
            db.commit()  # each identifier's work is kept even if a later one fails

        if not identifiers:
            errors.append({"identifier": None, "error": "no identifiers set (Settings > Sources)"})
        if ok_identifiers == 0:
            status = "failed"
        elif errors or counts["failed"]:
            status = "partial"
        else:
            status = "succeeded"
        db.execute(
            "DELETE FROM raw_postings WHERE fetched_at < now() - make_interval(days => %s)", (RAW_RETENTION_DAYS,)
        )
        row = db.execute(
            """
            UPDATE ingestion_runs SET finished_at = now(), status = %s, fetched = %s, inserted = %s,
                updated = %s, skipped = %s, failed = %s, errors = %s
            WHERE id = %s RETURNING *
            """,
            (status, counts["fetched"], counts["inserted"], counts["updated"], counts["skipped"], counts["failed"],
             Jsonb(errors), run_id),
        ).fetchone()  # fmt: skip
    if own_http:
        http.close()
    return row


def run_all(database_url: str | None = None, http: Http | None = None) -> list[dict]:
    with connect(database_url) as db:
        enabled = [r["source"] for r in db.execute("SELECT source FROM source_settings WHERE enabled ORDER BY source")]
    return [run_source(source, database_url, http) for source in enabled]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", choices=sorted(ADAPTERS), help="collect only this source")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    runs = [run_source(args.source)] if args.source else run_all()
    if not runs:
        print("No sources are enabled. Turn one on in Settings > Sources.")
    for r in runs:
        print(
            f"{r['source']}: {r['status']}. {r['fetched']} fetched, {r['inserted']} new, {r['updated']} updated, "
            f"{r['skipped']} unchanged or duplicate, {r['failed']} quarantined"
        )
        for e in r["errors"]:
            print(f"  - {e['identifier'] or '(settings)'}: {e['error']}")


if __name__ == "__main__":
    main()
