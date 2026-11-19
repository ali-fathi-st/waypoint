"""
Lever job sites: public, no key needed.

Identifier: the company slug, the part after jobs.lever.co/ in a careers
link, e.g. "leverdemo". Slugs are case-sensitive. (Boards on Lever's EU
instance use api.eu.lever.co; write the identifier as "eu:slug".)

API: GET https://api.lever.co/v0/postings/{slug}?mode=json
"""

from datetime import datetime, timezone

from app.ingestion.sources.base import Http, Invalid, Posting
from app.ingestion.text import detect_arrangement, detect_employment_type, html_to_text

NAME = "lever"
PAGE = 100


def _base(identifier: str) -> tuple[str, str]:
    if identifier.startswith("eu:"):
        return "https://api.eu.lever.co/v0/postings", identifier[3:]
    return "https://api.lever.co/v0/postings", identifier


def fetch(http: Http, identifier: str, context: dict) -> list[dict]:
    base, slug = _base(identifier)
    postings, skip = [], 0
    while True:
        page = http.get_json(f"{base}/{slug}", params={"mode": "json", "skip": skip, "limit": PAGE})
        if not isinstance(page, list):
            raise Invalid("unexpected response: expected a list of postings")
        postings += page
        if len(page) < PAGE or len(postings) >= 2000:
            return postings
        skip += PAGE


def _description(raw: dict) -> str:
    """The intro, each list ("Requirements", "Nice to have"...), then the closing text."""
    parts = [raw.get("descriptionPlain") or html_to_text(raw.get("description"))]
    for block in raw.get("lists") or []:
        heading = (block.get("text") or "").strip()
        body = html_to_text(block.get("content"))
        parts.append(f"{heading}\n\n{body}" if heading else body)
    parts.append(raw.get("additionalPlain") or html_to_text(raw.get("additional")))
    return "\n\n".join(p.strip() for p in parts if p and p.strip())


def normalize(raw: dict, identifier: str, context: dict) -> Posting:
    categories = raw.get("categories") or {}
    location = categories.get("location") or None
    title = raw.get("text") or ""
    workplace = (raw.get("workplaceType") or "").lower()
    arrangement = workplace if workplace in ("onsite", "remote", "hybrid") else detect_arrangement(location, title)
    salary = raw.get("salaryRange") or {}
    yearly = str(salary.get("interval", "")).startswith("per-year")
    created = raw.get("createdAt")
    _, slug = _base(identifier)
    return Posting(
        source_job_id=str(raw.get("id") or ""),
        title=title,
        company_name=context.get("company_name") or slug.replace("-", " ").title(),
        company_website=None,
        location=location,
        work_arrangement=arrangement,
        employment_type=detect_employment_type(categories.get("commitment")),
        description=_description(raw),
        url=raw.get("hostedUrl") or "",
        salary_min=int(salary["min"]) if yearly and salary.get("min") is not None else None,
        salary_max=int(salary["max"]) if yearly and salary.get("max") is not None else None,
        salary_currency=salary.get("currency") if yearly else None,
        posted_at=datetime.fromtimestamp(created / 1000, tz=timezone.utc) if isinstance(created, (int, float)) else None,
    ).check()
