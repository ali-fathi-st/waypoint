"""
Database connections.

Each request gets its own connection through get_db(). Rows come back as
dictionaries ({"title": "Data Engineer", ...}) instead of tuples, so code
can use column names.

psycopg's connection block commits when the request succeeds and rolls back
if anything raises, so a failed request never leaves half-written data.
"""

from collections.abc import Iterator

import psycopg
from psycopg.rows import dict_row

from app.config import get_settings


def connect(database_url: str | None = None) -> psycopg.Connection:
    """Open a connection. Rows are returned as dicts."""
    # TimeZone=UTC: timestamps come back in UTC, as the API contract says.
    return psycopg.connect(database_url or get_settings().database_url, row_factory=dict_row, options="-c TimeZone=UTC")


def get_db() -> Iterator[psycopg.Connection]:
    """FastAPI dependency: one connection per request, committed at the end."""
    with connect() as conn:
        yield conn
