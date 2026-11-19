"""
Shared test setup.

Tests run against the TEST database (TEST_DATABASE_URL, default waypoint_test),
never your real one. Before each test that uses `client`, the test database is
wiped, your migrations are applied, and the sample data is loaded, so every
test starts from the same known state.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import connect, get_db
from app.main import app
from db.migrate import migrate
from db.seed import seed

SEED = json.loads((Path(__file__).parent.parent / "db" / "seed" / "jobs.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = get_settings().test_database_url
    try:
        psycopg.connect(url, connect_timeout=3).close()
    except psycopg.OperationalError as error:
        pytest.exit(
            f"Can't reach the test database ({url}).\n"
            "Is PostgreSQL running? From the backend folder: docker compose up -d\n"
            f"Details: {error}",
            returncode=1,
        )
    return url


@pytest.fixture
def database(test_database_url):
    """A fresh test database: wiped, migrated, seeded."""
    # Every database test needs working tables, so if they can't be built,
    # stop the run with one clear message instead of dozens of errors.
    try:
        migrate(test_database_url, reset=True)
    except SystemExit as error:  # migrate.py explains what's wrong
        pytest.exit(f"Migration failed: {error}", returncode=1)
    try:
        seed(test_database_url)
    except psycopg.Error as error:
        pytest.exit(
            "The sample data didn't load into your tables. Compare your column names and types "
            f"with the spec in db/migrations/001_create_jobs.sql.\nDetails: {error}",
            returncode=1,
        )
    return test_database_url


@pytest.fixture
def db(database):
    """A direct connection to the test database, for checking what's stored."""
    with connect(database) as conn:
        yield conn


@pytest.fixture
def client(database):
    """An HTTP client for the API, wired to the test database."""

    def test_db():
        with connect(database) as conn:
            yield conn

    app.dependency_overrides[get_db] = test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seed_jobs() -> list[dict]:
    """The sample jobs, as they are in db/seed/jobs.json."""
    return SEED["jobs"]


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
