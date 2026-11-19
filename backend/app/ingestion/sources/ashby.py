"""
Ashby job boards: public, no key needed.

Identifier: the board name, the part after jobs.ashbyhq.com/ in a careers
link, e.g. "jobber".

API: GET https://api.ashbyhq.com/posting-api/job-board/{name}?includeCompensation=true
"""

from datetime import datetime

from app.ingestion.sources.base import Http, Invalid, Posting
from app.ingestion.text import detect_arrangement, detect_employment_type, html_to_text

NAME = "ashby"
TYPES = {"FullTime": "full_time", "PartTime": "part_time", "Intern": "internship", "Contract": "contract",
         "Temporary": "temporary"}  # fmt: skip
ARRANGEMENTS = {"onsite": "onsite", "remote": "remote", "hybrid": "hybrid"}


def fetch(http: Http, identifier: str, context: dict) -> list[dict]:
    data = http.get_json(
        f"https://api.ashbyhq.com/posting-api/job-board/{identifier}", params={"includeCompensation": "true"}
    )
    jobs = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(jobs, list):
        raise Invalid("unexpected response: no 'jobs' list")
    return [j for j in jobs if isinstance(j, dict) and j.get("isListed", True)]


def _location(raw: dict) -> str | None:
    places = [raw.get("location")] + [s.get("location") for s in raw.get("secondaryLocations") or [] if isinstance(s, dict)]
    places = [p for p in dict.fromkeys(places) if p]
    return "; ".join(places)[:300] or None


def _salary(raw: dict) -> tuple[int | None, int | None, str | None]:
    """A posted yearly salary range only; nothing estimated."""
    for part in (raw.get("compensation") or {}).get("summaryComponents") or []:
        if not isinstance(part, dict) or part.get("compensationType") != "Salary":
            continue
        if str(part.get("interval", "")).upper() not in ("1 YEAR", "YEAR", "ANNUAL"):
            continue
        low, high = part.get("minValue"), part.get("maxValue")
        if isinstance(low, (int, float)) and isinstance(high, (int, float)):
            return int(low), int(high), part.get("currencyCode")
    return None, None, None


def normalize(raw: dict, identifier: str, context: dict) -> Posting:
    location = _location(raw)
    title = raw.get("title") or ""
    workplace = str(raw.get("workplaceType") or "").lower().replace("-", "").replace("_", "")
    arrangement = ARRANGEMENTS.get(workplace) or ("remote" if raw.get("isRemote") else detect_arrangement(location, title))
    try:
        posted = datetime.fromisoformat(str(raw.get("publishedAt")).replace("Z", "+00:00"))
    except ValueError:
        posted = None
    salary_min, salary_max, currency = _salary(raw)
    return Posting(
        source_job_id=str(raw.get("id") or ""),
        title=title,
        company_name=context.get("company_name") or identifier.replace("-", " ").title(),
        company_website=None,
        location=location,
        work_arrangement=arrangement,
        employment_type=TYPES.get(raw.get("employmentType")) or detect_employment_type(raw.get("employmentType")),
        description=raw.get("descriptionPlain") or html_to_text(raw.get("descriptionHtml")),
        url=raw.get("jobUrl") or "",
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=currency,
        posted_at=posted,
    ).check()
