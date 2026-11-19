"""
Shared test setup.

Tests run against the TEST database (TEST_DATABASE_URL, default waypoint_test),
never your real one. Before each test that uses a database fixture, the test
database is wiped and migrated; `client` and `db` also load the fictional demo
data, so every test starts from the same known state. Uploaded files go to a
temporary folder.
"""

import json
import os

# The test client calls itself "testserver"; allow it before the app loads its settings.
os.environ["ALLOWED_HOSTS"] = "localhost,127.0.0.1,testserver"

from datetime import datetime, timezone
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import connect, get_db
from app.main import app
from db.migrate import migrate
from db.seed import load_demo, seed

ROOT = Path(__file__).parent.parent


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


@pytest.fixture(autouse=True)
def private_storage(tmp_path, monkeypatch):
    """Uploaded files go to a temporary folder, never your real storage."""
    monkeypatch.setattr(get_settings(), "storage_dir", str(tmp_path / "storage"))
    return tmp_path / "storage"


@pytest.fixture
def empty_database(test_database_url):
    """Tables created, nothing in them: what a brand-new install looks like."""
    try:
        migrate(test_database_url, reset=True)
    except SystemExit as error:
        pytest.exit(f"Migration failed: {error}", returncode=1)
    return test_database_url


@pytest.fixture
def database(empty_database):
    """The test database with the fictional demo data loaded."""
    seed(empty_database)
    return empty_database


def _client_for(url):
    def test_db():
        with connect(url) as conn:
            yield conn

    app.dependency_overrides[get_db] = test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def client(database):
    """An HTTP client for the API, on the demo data."""
    yield from _client_for(database)


@pytest.fixture
def empty_client(empty_database):
    """An HTTP client for the API, on an empty database."""
    yield from _client_for(empty_database)


@pytest.fixture
def db(database):
    """A direct connection to the test database, for checking what's stored."""
    with connect(database) as conn:
        yield conn


@pytest.fixture
def demo() -> dict:
    """The demo data as it was loaded (dates already moved to today)."""
    return load_demo()


@pytest.fixture
def seed_jobs(demo) -> list[dict]:
    return demo["jobs"]


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def contract_fields() -> dict[str, list[str]]:
    """The required fields per record, read straight from frontend/js/api/contract.js."""
    import re

    source = (ROOT.parent / "frontend" / "js" / "api" / "contract.js").read_text(encoding="utf-8")
    block = source[source.index("REQUIRED_FIELDS = {") : source.index("};")]
    return {
        kind: re.findall(r'"(\w+)"', body)
        for kind, body in re.findall(r"(\w+):\s*\[([^\]]*)\]", block)
    }


def load_json(name: str):
    return json.loads((Path(__file__).parent / "fixtures" / name).read_text(encoding="utf-8"))
