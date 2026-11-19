"""
What every job source provides. To add a source, write a module with:

    NAME = "mysource"
    def fetch(client: Http, identifier: str, context: dict) -> list[dict]
        Return the raw postings exactly as the source sent them.
    def normalize(raw: dict, identifier: str, context: dict) -> Posting
        Turn one raw posting into a Posting. Raise Invalid(reason) if it's
        unusable; it goes to quarantine with that reason instead of the jobs table.

and add it to ADAPTERS in sources/__init__.py (and to the CHECK lists in the
migrations). Only use official APIs or feeds you're allowed to use, and
respect their rate limits and terms.
"""

import time
from dataclasses import dataclass
from datetime import datetime

import httpx

USER_AGENT = "Waypoint/1.0 (personal job search tracker; one request at a time)"


class Invalid(ValueError):
    """A posting that can't be stored. The message says why."""


class SourceError(RuntimeError):
    """A whole request failed (not found, blocked, down). The message is shown in the run log."""


@dataclass
class Posting:
    source_job_id: str
    title: str
    company_name: str
    company_website: str | None
    location: str | None
    work_arrangement: str  # onsite | hybrid | remote | unknown
    employment_type: str  # full_time | part_time | contract | temporary | internship | unknown
    description: str  # plain text
    url: str
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    posted_at: datetime | None

    def check(self) -> "Posting":
        if not self.source_job_id:
            raise Invalid("missing the source's job id")
        if not self.title.strip():
            raise Invalid("missing a title")
        if not self.company_name.strip():
            raise Invalid("missing a company name")
        if not self.url.startswith(("https://", "http://")):
            raise Invalid(f"link isn't a web address: {self.url[:80]!r}")
        if self.salary_min is not None and self.salary_max is not None and self.salary_max < self.salary_min:
            self.salary_min = self.salary_max = self.salary_currency = None  # contradictory: don't guess
        self.title = self.title.strip()[:300]
        return self


class Http:
    """A polite HTTP client: identifies itself, waits between requests, retries briefly on 429/5xx."""

    def __init__(self, timeout: float = 20.0, delay: float = 1.0, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
        self.delay = delay
        self._last = 0.0
        self._robots: dict = {}

    def _get(self, url: str, params: dict | None = None) -> httpx.Response:
        for attempt in range(3):
            wait = self._last + self.delay - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            try:
                response = self.client.get(url, params=params)
            except httpx.HTTPError as error:
                if attempt == 2:
                    raise SourceError(f"couldn't connect: {error.__class__.__name__}") from error
                time.sleep(2**attempt)
                continue
            if response.status_code == 404:
                raise SourceError("not found (check the board name or company slug)")
            if response.status_code in (401, 403):
                raise SourceError(f"access refused ({response.status_code}); check credentials or permission")
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == 2:
                    raise SourceError(f"source unavailable ({response.status_code})")
                retry_after = response.headers.get("Retry-After", "")
                time.sleep(min(int(retry_after), 60) if retry_after.isdigit() else 2 ** (attempt + 1))
                continue
            if response.status_code >= 400:
                raise SourceError(f"request failed ({response.status_code})")
            return response
        raise SourceError("gave up after retries")

    def get_json(self, url: str, params: dict | None = None):
        response = self._get(url, params)
        try:
            return response.json()
        except ValueError as error:
            raise SourceError("the source didn't return JSON") from error

    def get_text(self, url: str, params: dict | None = None, max_bytes: int = 10_000_000) -> str:
        response = self._get(url, params)
        if len(response.content) > max_bytes:
            raise SourceError("the response is too large")
        return response.text

    def allowed_by_robots(self, url: str) -> bool:
        """Does the site's robots.txt allow fetching this URL? (No robots.txt = allowed.)"""
        from urllib.parse import urlsplit
        from urllib.robotparser import RobotFileParser

        parts = urlsplit(url)
        robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
        if robots_url not in self._robots:
            parser = RobotFileParser()
            try:
                parser.parse(self.get_text(robots_url, max_bytes=500_000).splitlines())
            except SourceError as error:
                if "not found" not in str(error):
                    raise
                parser.parse([])
            self._robots[robots_url] = parser
        return self._robots[robots_url].can_fetch(USER_AGENT, url)

    def close(self):
        self.client.close()
