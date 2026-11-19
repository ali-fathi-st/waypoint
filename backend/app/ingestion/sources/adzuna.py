"""
Adzuna job search: needs a free app id and key (developer.adzuna.com), set as
ADZUNA_APP_ID and ADZUNA_APP_KEY in backend/.env. Never in the website.

Identifier: a search term, e.g. "data engineer". Each term is searched in
each of your profile's locations (or the whole country if you have none).
Adzuna only returns a short snippet of each description, so skills found
(and the match score) are less complete than for Greenhouse or Lever.

API: GET https://api.adzuna.com/v1/api/jobs/{country}/search/1
"""

from datetime import datetime

from app.config import get_settings
from app.ingestion.sources.base import Http, Invalid, Posting, SourceError
from app.ingestion.text import detect_arrangement, html_to_text

NAME = "adzuna"
CURRENCY = {"ca": "CAD", "us": "USD", "gb": "GBP", "au": "AUD", "nz": "NZD", "in": "INR", "sg": "SGD"}


def fetch(http: Http, identifier: str, context: dict) -> list[dict]:
    cfg = get_settings()
    if not (cfg.adzuna_app_id and cfg.adzuna_app_key):
        raise SourceError("ADZUNA_APP_ID and ADZUNA_APP_KEY aren't set in backend/.env")
    country = cfg.adzuna_country.lower()
    wheres = [loc.split(",")[0].strip() for loc in context.get("locations") or []] or [None]
    results = []
    for where in wheres:
        params = {
            "app_id": cfg.adzuna_app_id,
            "app_key": cfg.adzuna_app_key,
            "what": identifier,
            "results_per_page": 50,
            "content-type": "application/json",
        }
        if where:
            params["where"] = where
        data = http.get_json(f"https://api.adzuna.com/v1/api/jobs/{country}/search/1", params=params)
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise Invalid("unexpected response: no 'results' list")
        results += data["results"]
    context["country"] = country
    return results


def normalize(raw: dict, identifier: str, context: dict) -> Posting:
    location = (raw.get("location") or {}).get("display_name") or None
    title = html_to_text(raw.get("title"))
    predicted = str(raw.get("salary_is_predicted", "0")) == "1"  # Adzuna's estimate, not posted: ignore
    contract_time = raw.get("contract_time")
    if raw.get("contract_type") == "contract":
        employment = "contract"
    elif contract_time in ("full_time", "part_time"):
        employment = contract_time
    else:
        employment = "unknown"
    try:
        posted = datetime.fromisoformat(str(raw.get("created")).replace("Z", "+00:00"))
    except ValueError:
        posted = None
    company = (raw.get("company") or {}).get("display_name") or ""
    if not company:
        raise Invalid("missing a company name")
    return Posting(
        source_job_id=str(raw.get("id") or ""),
        title=title,
        company_name=company,
        company_website=None,
        location=location,
        work_arrangement=detect_arrangement(location, title),
        employment_type=employment,
        description=html_to_text(raw.get("description")),
        url=raw.get("redirect_url") or "",
        salary_min=None if predicted or raw.get("salary_min") is None else int(raw["salary_min"]),
        salary_max=None if predicted or raw.get("salary_max") is None else int(raw["salary_max"]),
        salary_currency=None if predicted or raw.get("salary_min") is None else CURRENCY.get(context.get("country", "")),
        posted_at=posted,
    ).check()
