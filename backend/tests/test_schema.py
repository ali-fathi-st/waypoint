"""
The tables and the rules the database enforces itself. These read the
database directly, so they check the SQL in db/migrations/.
"""

import psycopg
import pytest

EXPECTED_JOB_COLUMNS = {
    # column: (type, nullable)
    "id": ("text", False),
    "source": ("text", False),
    "source_job_id": ("text", False),
    "title": ("text", False),
    "company_id": ("text", False),
    "location": ("text", True),
    "work_arrangement": ("text", False),
    "employment_type": ("text", False),
    "description": ("text", False),
    "url": ("text", False),
    "salary_min": ("integer", True),
    "salary_max": ("integer", True),
    "salary_currency": ("text", True),
    "posted_at": ("timestamp with time zone", True),
    "first_seen_at": ("timestamp with time zone", False),
    "last_seen_at": ("timestamp with time zone", False),
    "review_status": ("text", False),
    "skills": ("jsonb", False),
    "match": ("jsonb", True),
    "match_score": ("integer", True),
    "content_hash": ("text", True),
    "dedupe_key": ("text", True),
}


def columns(db, table):
    rows = db.execute(
        "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = %s",
        (table,),
    ).fetchall()
    return {r["column_name"]: (r["data_type"], r["is_nullable"] == "YES") for r in rows}


def insert_job(db, **changes):
    """Insert one valid job, with some values changed. Used to test the rules."""
    job = {
        "id": "job_test",
        "source": "manual",
        "source_job_id": "test-1",
        "title": "Test job",
        "company_id": "co_northline",
        "work_arrangement": "remote",
        "employment_type": "full_time",
        "description": "A test.",
        "url": "https://example.com/test",
        **changes,
    }
    names = ", ".join(job)
    placeholders = ", ".join(["%s"] * len(job))
    db.execute(f"INSERT INTO jobs ({names}) VALUES ({placeholders})", tuple(job.values()))


def test_companies_table(db):
    assert columns(db, "companies") == {
        "id": ("text", False),
        "name": ("text", False),
        "website": ("text", True),
    }


def test_jobs_table_has_every_column(db):
    actual = columns(db, "jobs")
    missing = sorted(set(EXPECTED_JOB_COLUMNS) - set(actual))
    assert not missing, f"jobs is missing columns: {missing}"
    for name, (data_type, nullable) in EXPECTED_JOB_COLUMNS.items():
        assert actual[name][0] == data_type, f"jobs.{name} should be {data_type}, not {actual[name][0]}"
        assert actual[name][1] == nullable, f"jobs.{name} should be {'NULL' if nullable else 'NOT NULL'}"


def test_sample_data_loaded(db, demo):
    assert db.execute("SELECT count(*) AS n FROM jobs").fetchone()["n"] == len(demo["jobs"])
    assert db.execute("SELECT count(*) AS n FROM companies").fetchone()["n"] == len(demo["companies"])
    assert db.execute("SELECT count(*) AS n FROM applications").fetchone()["n"] == len(demo["applications"])
    assert db.execute("SELECT count(*) AS n FROM documents").fetchone()["n"] == len(demo["documents"])


def test_defaults(db):
    insert_job(db)
    row = db.execute("SELECT * FROM jobs WHERE id = 'job_test'").fetchone()
    assert row["review_status"] == "new"
    assert row["skills"] == []
    assert row["first_seen_at"] is not None
    assert row["last_seen_at"] is not None
    assert row["match"] is None


def test_same_posting_cannot_be_stored_twice(db):
    insert_job(db)
    with pytest.raises(psycopg.errors.UniqueViolation):
        insert_job(db, id="job_test_2")  # different id, same source + source_job_id


def test_same_source_id_from_another_source_is_fine(db):
    insert_job(db)
    insert_job(db, id="job_test_2", source="lever")


def test_company_must_exist(db):
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        insert_job(db, company_id="co_does_not_exist")


@pytest.mark.parametrize(
    "column, bad_value",
    [
        ("source", "linkedin"),
        ("work_arrangement", "sometimes"),
        ("employment_type", "gig"),
        ("review_status", "maybe"),
        ("match_score", 101),
        ("match_score", -1),
        ("salary_min", -5),
    ],
)
def test_bad_values_are_rejected(db, column, bad_value):
    with pytest.raises(psycopg.errors.CheckViolation):
        insert_job(db, **{column: bad_value})


def test_salary_max_cannot_be_below_min(db):
    with pytest.raises(psycopg.errors.CheckViolation):
        insert_job(db, salary_min=90000, salary_max=80000)


def test_required_columns(db):
    with pytest.raises(psycopg.errors.NotNullViolation):
        insert_job(db, title=None)


@pytest.mark.parametrize("column", ["review_status", "first_seen_at", "match_score"])
def test_indexes(db, column):
    indexes = db.execute("SELECT indexdef FROM pg_indexes WHERE tablename = 'jobs'").fetchall()
    assert any(f"({column}" in r["indexdef"] for r in indexes), f"add an index on jobs.{column}"


def insert_application(db, **changes):
    row = {"id": "app_test", "job_id": "job_001", **changes}
    names = ", ".join(row)
    db.execute(f"INSERT INTO applications ({names}) VALUES ({', '.join(['%s'] * len(row))})", tuple(row.values()))


def test_one_application_per_job(db):
    insert_application(db)
    with pytest.raises(psycopg.errors.UniqueViolation):
        insert_application(db, id="app_test_2")


def test_follow_up_needs_an_open_application(db):
    with pytest.raises(psycopg.errors.CheckViolation):
        insert_application(db, status="rejected", follow_up_at="2026-01-01")


def test_follow_up_not_before_applied(db):
    with pytest.raises(psycopg.errors.CheckViolation):
        insert_application(db, status="applied", applied_at="2026-02-01", follow_up_at="2026-01-01")


def test_document_versions_are_unique_per_type_and_job(db):
    row = "INSERT INTO documents (id, document_type, title, version, origin) VALUES (%s, 'resume', 'R', 1, 'uploaded')"
    db.execute("DELETE FROM documents WHERE document_type = 'resume' AND version = 1")
    db.execute(row, ("doc_a",))
    with pytest.raises(psycopg.errors.UniqueViolation):
        db.execute(row, ("doc_b",))


def test_settings_have_exactly_one_row(db):
    with pytest.raises(psycopg.errors.IntegrityError):
        db.execute("INSERT INTO app_settings (id, notifications, account) VALUES (2, '{}', '{}')")


def test_months_are_checked(db):
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            "INSERT INTO candidate_experience (id, profile_id, position, title, company, start_month) "
            "VALUES ('e', 'me', 9, 'T', 'C', '2025-13')"
        )
