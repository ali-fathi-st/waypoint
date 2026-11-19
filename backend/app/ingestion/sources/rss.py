"""
Employers' public RSS job feeds, e.g. the Government of Alberta's.

Identifier: the feed's full address (https only). For the Government of
Alberta, search on jobpostings.alberta.ca and use its feed link, which looks
like  https://jobpostings.alberta.ca/feeds/data/?locale=en_US  ("data" is the
search word).

Feeds are only read when the site's robots.txt allows it. Feed XML is
untrusted, so it's parsed with defusedxml (no external entities, no
"billion laughs").
"""

import re
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

from defusedxml import ElementTree

from app.ingestion.sources.base import Http, Invalid, Posting, SourceError
from app.ingestion.text import detect_arrangement, detect_employment_type, html_to_text

NAME = "rss"
ATOM = "{http://www.w3.org/2005/Atom}"
TRAILING_PLACE = re.compile(r"^(?P<title>.*\S)\s*\((?P<place>[^()]*,\s*[A-Za-z]{2,3})\)\s*$")
YEARLY = re.compile(
    r"\$\s?(?P<low>[\d,]{4,}(?:\.\d+)?)\s*(?:-|–|to)\s*\$\s?(?P<high>[\d,]{4,}(?:\.\d+)?)\s*"
    r"(?:/\s*|per\s+)?(?:year|yr|annum|annually|annual)",
    re.I,
)


def fetch(http: Http, identifier: str, context: dict) -> list[dict]:
    if urlsplit(identifier).scheme != "https":
        raise SourceError("feed addresses must start with https://")
    if not http.allowed_by_robots(identifier):
        raise SourceError("this site's robots.txt doesn't allow reading that address")
    try:
        root = ElementTree.fromstring(http.get_text(identifier))
    except ElementTree.ParseError as error:
        raise SourceError(f"not a valid feed ({error})") from error
    except Exception as error:  # defusedxml refuses unsafe XML (entities, DTDs)
        raise SourceError(f"feed refused as unsafe: {error.__class__.__name__}") from error

    channel = root.find("channel")
    if channel is not None:  # RSS 2.0
        feed_title = channel.findtext("title") or ""
        items = [
            {"title": i.findtext("title"), "link": i.findtext("link"), "guid": i.findtext("guid"),
             "description": i.findtext("description"), "published": i.findtext("pubDate")}
            for i in channel.findall("item")
        ]  # fmt: skip
    elif root.tag == f"{ATOM}feed":  # Atom
        feed_title = root.findtext(f"{ATOM}title") or ""
        items = []
        for e in root.findall(f"{ATOM}entry"):
            link = e.find(f"{ATOM}link")
            items.append({
                "title": e.findtext(f"{ATOM}title"), "link": link.get("href") if link is not None else None,
                "guid": e.findtext(f"{ATOM}id"),
                "description": e.findtext(f"{ATOM}content") or e.findtext(f"{ATOM}summary"),
                "published": e.findtext(f"{ATOM}published") or e.findtext(f"{ATOM}updated"),
            })  # fmt: skip
    else:
        raise SourceError("not an RSS or Atom feed")
    # "Government of Alberta - Custom Search data" -> "Government of Alberta"
    context["company_name"] = re.split(r"\s+[-–|]\s+", feed_title.strip())[0] or urlsplit(identifier).netloc
    return items


def _field(text: str, *names: str) -> str | None:
    """'Full or Part-Time: Full Time' -> 'Full Time'."""
    for name in names:
        m = re.search(rf"^\s*{re.escape(name)}\s*:\s*(.+)$", text, re.I | re.M)
        if m:
            return m.group(1).strip()
    return None


def _date(value: str | None):
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        from datetime import datetime

        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None


def normalize(raw: dict, identifier: str, context: dict) -> Posting:
    title = html_to_text(raw.get("title") or "")
    location = None
    m = TRAILING_PLACE.match(title)
    if m:
        title, location = m.group("title"), m.group("place").strip()
    description = html_to_text(raw.get("description"))
    location = location or _field(description, "Location")
    kind = " ".join(filter(None, [
        _field(description, "Permanent/Temporary/Wage", "Permanent/Temporary", "Job Type", "Employment Type"),
        _field(description, "Full or Part-Time", "Full/Part Time"),
    ]))  # fmt: skip
    employment = detect_employment_type(kind)
    if employment == "unknown" and "temporary" in kind.lower():
        employment = "temporary"
    salary = YEARLY.search(description)
    link = (raw.get("link") or "").strip()
    if not link:
        raise Invalid("missing a link")
    return Posting(
        source_job_id=(raw.get("guid") or link).strip()[:500],
        title=title,
        company_name=context.get("company_name") or urlsplit(identifier).netloc,
        company_website=None,
        location=location[:300] if location else None,
        work_arrangement=detect_arrangement(location, title),
        employment_type=employment,
        description=description,
        url=link,
        salary_min=int(float(salary["low"].replace(",", ""))) if salary else None,
        salary_max=int(float(salary["high"].replace(",", ""))) if salary else None,
        salary_currency="CAD" if salary and urlsplit(identifier).netloc.endswith(".ca") else None,
        posted_at=_date(raw.get("published")),
    ).check()
