"""
Greenhouse job boards: public, no key needed.

Identifier: the board token, the part after boards.greenhouse.io/ (or
job-boards.greenhouse.io/) in a company's careers link, e.g. "gitlab".

API: GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
     GET https://boards-api.greenhouse.io/v1/boards/{token}  (the company name)
"""

from datetime import datetime

from app.ingestion.sources.base import Http, Invalid, Posting
from app.ingestion.text import detect_arrangement, detect_employment_type, html_to_text

NAME = "greenhouse"
BASE = "https://boards-api.greenhouse.io/v1/boards"


def fetch(http: Http, identifier: str, context: dict) -> list[dict]:
    try:
        context["company_name"] = http.get_json(f"{BASE}/{identifier}").get("name") or identifier
    except Exception:  # the name is nice to have; the jobs are what matter
        context["company_name"] = identifier.replace("-", " ").title()
    data = http.get_json(f"{BASE}/{identifier}/jobs", params={"content": "true", "pay_transparency": "true"})
    jobs = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(jobs, list):
        raise Invalid("unexpected response: no 'jobs' list")
    return jobs


def _metadata(raw: dict, *names: str) -> str | None:
    for item in raw.get("metadata") or []:
        if isinstance(item, dict) and str(item.get("name", "")).lower() in names:
            value = item.get("value")
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            return str(value) if value else None
    return None


def _salary(raw: dict) -> tuple[int | None, int | None, str | None]:
    """Only a posted annual range counts; nothing is estimated."""
    for pay in raw.get("pay_input_ranges") or []:
        try:
            low, high = int(pay["min_cents"]) // 100, int(pay["max_cents"]) // 100
        except (KeyError, TypeError, ValueError):
            continue
        if low >= 10_000:  # below that it's hourly, not a yearly salary
            return low, high, pay.get("currency_type")
    return None, None, None


def _time(value) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")) if value else None
    except ValueError:
        return None


def normalize(raw: dict, identifier: str, context: dict) -> Posting:
    location = (raw.get("location") or {}).get("name") or None
    title = raw.get("title") or ""
    salary_min, salary_max, currency = _salary(raw)
    return Posting(
        source_job_id=str(raw.get("id") or ""),
        title=title,
        company_name=raw.get("company_name") or context.get("company_name") or identifier,
        company_website=None,
        location=location,
        work_arrangement=detect_arrangement(location, title, _metadata(raw, "workplace type", "work arrangement")),
        employment_type=detect_employment_type(_metadata(raw, "employment type", "job type", "employment")),
        description=html_to_text(raw.get("content")),
        url=raw.get("absolute_url") or "",
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=currency,
        posted_at=_time(raw.get("first_published")),
    ).check()
