"""Small helpers shared by the routers."""

import uuid
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException


def new_id(prefix: str) -> str:
    """A unique id like 'app_3f2a...'. The prefix tells you what it is."""
    return f"{prefix}_{uuid.uuid4().hex}"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or "America/Edmonton")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("America/Edmonton")


def today_in(tz_name: str | None) -> date:
    """Today's date where the user is (not in UTC)."""
    return utc_now().astimezone(zone(tz_name)).date()


def format_date(value: date) -> str:
    """'Nov 19, 2026', the same as the website shows."""
    return f"{value:%b} {value.day}, {value.year}"


def not_found(what: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{what} not found")


def invalid(message: str, field: str | None = None) -> HTTPException:
    """A 422 in FastAPI's own format, so the website can show it under the field."""
    if field is None:
        return HTTPException(status_code=422, detail=message)
    return HTTPException(
        status_code=422, detail=[{"loc": ["body", field], "msg": message, "type": "value_error"}]
    )


def conflict(message: str) -> HTTPException:
    return HTTPException(status_code=409, detail=message)


def account_timezone(db) -> str:
    row = db.execute("SELECT account->>'timezone' AS tz FROM app_settings WHERE id = 1").fetchone()
    return row["tz"] if row else "America/Edmonton"
