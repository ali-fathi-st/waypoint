"""Ashby, RSS feeds (with robots.txt), and keeping only jobs in your area."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.db import connect
from app.ingestion.run import run_source
from app.ingestion.sources.base import SourceError
from app.services.area import in_area, remote_open_to_you, user_area
from app.services.matching import score_job
from tests.conftest import load_json
from tests.test_ingestion import FakeHttp, configure, count, jobs

FIXTURES = Path(__file__).parent / "fixtures"
AB = "https://api.ashbyhq.com/posting-api/job-board/exampleco"
FEED = "https://jobpostings.alberta.ca/feeds/data/?locale=en_US"
ROBOTS = "https://jobpostings.alberta.ca/robots.txt"
GOA_ROBOTS = "User-agent: *\nDisallow: /services/\nDisallow: /talentcommunity/\n"


class TextHttp(FakeHttp):
    """FakeHttp that can also answer text requests (feeds, robots.txt)."""

    def get_text(self, url, params=None, max_bytes=0):
        return self.get_json(url, params)

    def allowed_by_robots(self, url):
        from app.ingestion.sources.base import Http

        real = Http.__new__(Http)
        real._robots = {}
        real.get_text = self.get_text
        return Http.allowed_by_robots(real, url)


def feed_http(robots=GOA_ROBOTS):
    responses = {FEED: (FIXTURES / "goa_feed.xml").read_text(encoding="utf-8")}
    responses[ROBOTS] = robots if robots is not None else SourceError("not found (check the board name or company slug)")
    return TextHttp(responses)


# ---------------------------------------------------------------- area rules
EDMONTON = user_area(["Edmonton, AB", "Calgary, AB"])


@pytest.mark.parametrize(
    "location, arrangement, expected",
    [
        ("Edmonton, Alberta, Canada", "onsite", True),
        ("Calgary", "hybrid", True),
        ("Various, AB", "unknown", True),
        ("Red Deer, AB", "onsite", True),
        ("Toronto, ON", "onsite", False),
        ("Remote - Canada", "remote", True),
        ("Remote, Canada; Remote, United States", "remote", True),
        ("Remote, United States", "remote", False),
        ("Remote - EMEA", "remote", False),
        ("Remote", "remote", True),
        (None, "remote", True),
        ("Anywhere (Remote)", "remote", True),
        ("San Francisco, CA", "onsite", False),
        ("Remote - SF Bay Area", "remote", False),
        ("Remote (New York or Seattle)", "remote", False),
        ("Remote, South Korea", "remote", False),
        ("Remote - ME; Remote - NH; Remote - VT", "remote", False),
        ("Remote (Canada)", "remote", True),
        ("KOHO (CAN)", "remote", True),
        ("Remote - HQ", "remote", True),
    ],
)  # fmt: skip
def test_in_area(location, arrangement, expected):
    assert in_area(location, arrangement, EDMONTON) is expected


def test_no_locations_means_everything_counts():
    assert in_area("Tokyo, Japan", "onsite", user_area([]))
    assert remote_open_to_you("Remote, United States", user_area([]))


def test_us_remote_scores_zero_for_location():
    profile = {"skills": [], "preferred_titles": [], "exclusions": [], "locations": ["Edmonton, AB"],
               "work_arrangements": ["remote"], "salary_min": None}  # fmt: skip
    job = {"id": "j", "title": "X", "skills": [], "work_arrangement": "remote", "salary_max": None}
    def location_factor(where):
        factors = score_job({**job, "location": where}, profile, datetime.now(timezone.utc))["factors"]
        return next(f for f in factors if f["key"] == "location")

    us, ca = location_factor("Remote, United States"), location_factor("Remote - Canada")
    assert us["score"] == 0 and "only for people in" in us["detail"]
    assert ca["score"] == 1


# ---------------------------------------------------------------- ashby
def test_ashby(empty):
    configure(empty, "ashby", ["exampleco"])
    run = run_source("ashby", empty, FakeHttp({AB: load_json("ashby_board.json")}))
    assert run["fetched"] == 2, "unlisted jobs are ignored"
    assert run["inserted"] == 1 and run["outside_area"] == 1, "the US-only remote job is skipped"
    (job,) = jobs(empty, "ashby")
    assert job["location"] == "Edmonton; Calgary" and job["work_arrangement"] == "hybrid"
    assert (job["salary_min"], job["salary_max"], job["salary_currency"]) == (75000, 90000, "CAD")
    assert job["employment_type"] == "full_time" and job["posted_at"] is not None
    assert {s["name"]: s["required"] for s in job["skills"]} == {"SQL": True, "Power BI": True, "Python": False}


# ---------------------------------------------------------------- rss
def test_goa_feed(empty):
    configure(empty, "rss", [FEED])
    run = run_source("rss", empty, feed_http())
    assert (run["fetched"], run["inserted"], run["outside_area"]) == (3, 2, 1), "Toronto is outside your area"
    analyst = next(j for j in jobs(empty, "rss") if "Research" in j["title"])
    assert analyst["title"] == "Data and Research Analyst" and analyst["location"] == "Edmonton, AB"
    assert analyst["company_name"] == "Government of Alberta"
    assert analyst["employment_type"] == "temporary"
    assert (analyst["salary_min"], analyst["salary_max"], analyst["salary_currency"]) == (68609, 89930, "CAD")
    assert analyst["posted_at"] is not None
    assert {s["name"]: s["required"] for s in analyst["skills"]} == {"SQL": True, "Power BI": True, "Python": False}
    officer = next(j for j in jobs(empty, "rss") if "Correctional" in j["title"])
    assert officer["title"] == "Correctional Peace Officer (CPO 1 & 2) (Multiple Locations)"
    assert officer["location"] == "Various, AB"


def test_feeds_robots_txt_disallows_are_respected(empty):
    blocked = "https://jobpostings.alberta.ca/services/rss/job/?locale=en_US&keywords=data"
    configure(empty, "rss", [blocked])
    http = feed_http()
    http.responses[blocked] = http.responses[FEED]
    run = run_source("rss", empty, http)
    assert run["status"] == "failed" and "robots.txt" in run["errors"][0]["error"]
    assert blocked not in [url for url, _ in http.calls], "the blocked address was never requested"
    assert count(empty, "jobs") == 0


def test_no_robots_txt_means_allowed(empty):
    configure(empty, "rss", [FEED])
    assert run_source("rss", empty, feed_http(robots=None))["inserted"] == 2


def test_feeds_must_be_https(empty):
    configure(empty, "rss", ["http://jobpostings.alberta.ca/feeds/data/"])
    run = run_source("rss", empty, feed_http())
    assert run["status"] == "failed" and "https" in run["errors"][0]["error"]


def test_unsafe_xml_is_refused(empty):
    bomb = ('<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;">]>'
            "<rss><channel><title>x</title><item><title>&lol2;</title></item></channel></rss>")  # fmt: skip
    configure(empty, "rss", [FEED])
    http = feed_http()
    http.responses[FEED] = bomb
    run = run_source("rss", empty, http)
    assert run["status"] == "failed" and "unsafe" in run["errors"][0]["error"]


@pytest.fixture
def empty(empty_database):
    return empty_database


def test_postings_with_no_skills_get_half_marks_not_full():
    profile = {"skills": [{"name": "SQL"}], "preferred_titles": [], "exclusions": [], "locations": [],
               "work_arrangements": [], "salary_min": None}  # fmt: skip
    job = {"id": "j", "title": "X", "skills": [], "location": None, "work_arrangement": "unknown", "salary_max": None}
    match = score_job(job, profile, datetime.now(timezone.utc))
    skills = [f for f in match["factors"] if f["key"].endswith("_skills")]
    assert [f["score"] for f in skills] == [0.5, 0.5]
    assert match["summary"].startswith("No skills found")


def test_feed_links_lose_tracking_parameters(empty):
    configure(empty, "rss", [FEED])
    http = feed_http()
    http.responses[FEED] = http.responses[FEED].replace(
        "605081517/</link>", "605081517/?feedId=null&amp;utm_source=J2WRSS&amp;utm_medium=rss</link>"
    )
    run_source("rss", empty, http)
    analyst = next(j for j in jobs(empty, "rss") if "Research" in j["title"])
    assert analyst["url"] == "https://jobpostings.alberta.ca/job/Edmonton-Data-and-Research-Analyst/605081517/"


def test_skip_words_in_titles_are_not_stored(empty):
    configure(empty, "greenhouse", ["exampleco"])
    with connect(empty) as db:
        db.execute("UPDATE candidate_profile SET exclusions = '{analytics}'")
    from tests.test_ingestion import gh_http

    run = run_source("greenhouse", empty, gh_http())
    assert run["excluded_title"] == 1, "Remote Analytics Engineer has a skip word"
    assert [j["title"] for j in jobs(empty, "greenhouse")] == ["Data Engineer"]
