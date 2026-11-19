"""
Job collection, against recorded responses (tests never call the real job
boards). Checks the pipeline rules: raw kept, bad rows quarantined, changes
detected, cross-source duplicates skipped, your review status preserved,
failures reported rather than hidden.
"""

import copy

import pytest

from app.db import connect
from app.ingestion.run import run_source
from app.ingestion.skills import extract_skills
from app.ingestion.sources.base import SourceError
from app.ingestion.text import detect_employment_type, html_to_text
from tests.conftest import load_json


class FakeHttp:
    """Answers from fixtures by URL. Anything else fails like a missing board."""

    def __init__(self, responses: dict):
        self.responses = responses
        self.calls: list[tuple[str, dict]] = []

    def get_json(self, url, params=None):
        self.calls.append((url, params or {}))
        if url not in self.responses:
            raise SourceError("not found (check the board name or company slug)")
        value = self.responses[url]
        if isinstance(value, Exception):
            raise value
        return copy.deepcopy(value)


GH = "https://boards-api.greenhouse.io/v1/boards/exampleco"
LV = "https://api.lever.co/v0/postings/exampleco"
AZ = "https://api.adzuna.com/v1/api/jobs/ca/search/1"


def gh_http(jobs=None):
    return FakeHttp({GH: load_json("greenhouse_board.json"), GH + "/jobs": jobs or load_json("greenhouse_jobs.json")})


@pytest.fixture
def empty(empty_database):
    return empty_database


def configure(url, source, identifiers, enabled=True):
    with connect(url) as db:
        db.execute(
            "UPDATE source_settings SET enabled = %s, identifiers = %s WHERE source = %s", (enabled, identifiers, source)
        )
        db.execute(
            "UPDATE candidate_profile SET preferred_titles = '{Data Engineer}', locations = '{\"Edmonton, AB\"}', "
            "work_arrangements = '{hybrid,remote,onsite}', salary_min = 75000"
        )
        db.execute("DELETE FROM candidate_skills")
        for i, name in enumerate(["SQL", "Python"]):
            db.execute(
                "INSERT INTO candidate_skills (profile_id, position, name, proficiency) VALUES ('me', %s, %s, 'proficient')",
                (i, name),
            )


def jobs(url, source=None):
    with connect(url) as db:
        sql = "SELECT j.*, c.name AS company_name FROM jobs j JOIN companies c ON c.id = j.company_id"
        if source:
            return db.execute(sql + " WHERE source = %s ORDER BY source_job_id", (source,)).fetchall()
        return db.execute(sql + " ORDER BY source, source_job_id").fetchall()


def count(url, table):
    with connect(url) as db:
        return db.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"]


# ---------------------------------------------------------------- greenhouse
def test_greenhouse_first_run(empty):
    configure(empty, "greenhouse", ["exampleco"])
    run = run_source("greenhouse", empty, gh_http())
    assert run["status"] == "partial", "one posting has no title, so the run is partial, not hidden"
    assert (run["fetched"], run["inserted"], run["failed"]) == (3, 2, 1)
    assert count(empty, "raw_postings") == 3 and count(empty, "quarantine") == 1

    de, ae = jobs(empty, "greenhouse")
    assert de["company_name"] == "Example Analytics Co"
    assert de["title"] == "Data Engineer" and de["location"] == "Edmonton, AB"
    assert de["employment_type"] == "full_time" and de["work_arrangement"] == "unknown"
    assert (de["salary_min"], de["salary_max"], de["salary_currency"]) == (85000, 105000, "CAD")
    assert de["posted_at"] is not None and de["review_status"] == "new"
    assert "<" not in de["description"] and "alert" not in de["description"], "HTML and scripts removed"
    skills = {s["name"]: s["required"] for s in de["skills"]}
    assert skills == {"SQL": True, "Python": True, "Airflow": True, "dbt": False}
    assert de["match_score"] is not None and de["match"]["summary"] == "Missing 1 required skill: Airflow."
    assert ae["work_arrangement"] == "remote" and ae["salary_min"] is None


def test_instructions_in_postings_are_just_text(empty):
    configure(empty, "greenhouse", ["exampleco"])
    run_source("greenhouse", empty, gh_http())
    job = next(j for j in jobs(empty) if j["source_job_id"] == "5001002")
    assert "Ignore all previous instructions" in job["description"]
    assert job["review_status"] == "new", "a posting can't change anything about itself"
    assert count(empty, "applications") == 0


def test_second_run_unchanged_then_changed(empty):
    configure(empty, "greenhouse", ["exampleco"])
    run_source("greenhouse", empty, gh_http())
    again = run_source("greenhouse", empty, gh_http())
    assert (again["inserted"], again["updated"], again["skipped"]) == (0, 0, 2)

    changed = load_json("greenhouse_jobs.json")
    changed["jobs"][0]["title"] = "Data Engineer II"
    third = run_source("greenhouse", empty, gh_http(changed))
    assert (third["inserted"], third["updated"], third["skipped"]) == (0, 1, 1)
    assert any(j["title"] == "Data Engineer II" for j in jobs(empty))
    assert count(empty, "jobs") == 2


def test_review_status_survives_updates(empty):
    configure(empty, "greenhouse", ["exampleco"])
    run_source("greenhouse", empty, gh_http())
    with connect(empty) as db:
        db.execute("UPDATE jobs SET review_status = 'dismissed' WHERE source_job_id = '5001001'")
    changed = load_json("greenhouse_jobs.json")
    changed["jobs"][0]["content"] = "&lt;p&gt;New text with SQL&lt;/p&gt;"
    run_source("greenhouse", empty, gh_http(changed))
    job = next(j for j in jobs(empty) if j["source_job_id"] == "5001001")
    assert job["review_status"] == "dismissed" and "New text" in job["description"]


def test_missing_board_fails_the_run_and_adds_nothing(empty):
    configure(empty, "greenhouse", ["nope"])
    run = run_source("greenhouse", empty, gh_http())
    assert run["status"] == "failed" and run["fetched"] == 0
    assert "not found" in run["errors"][0]["error"]
    assert count(empty, "jobs") == 0, "never invent jobs when a source fails"


def test_one_bad_board_makes_the_run_partial(empty):
    configure(empty, "greenhouse", ["exampleco", "nope"])
    run = run_source("greenhouse", empty, gh_http())
    assert run["status"] == "partial" and run["inserted"] == 2
    assert [e["identifier"] for e in run["errors"]] == ["nope"]


def test_no_identifiers(empty):
    configure(empty, "greenhouse", [])
    assert run_source("greenhouse", empty, gh_http())["status"] == "failed"


# ---------------------------------------------------------------- lever
def test_lever(empty):
    configure(empty, "lever", ["exampleco"])
    http = FakeHttp({LV: load_json("lever_postings.json")})
    run = run_source("lever", empty, http)
    assert (run["inserted"], run["failed"]) == (2, 1), "the javascript: link is quarantined"
    assert http.calls[0][1]["mode"] == "json"
    de, da = jobs(empty, "lever")
    assert de["work_arrangement"] == "hybrid" and de["employment_type"] == "full_time"
    assert de["salary_min"] == 85000 and de["company_name"] == "Exampleco"
    assert {s["name"]: s["required"] for s in de["skills"]}["dbt"] is False
    assert "Requirements" in de["description"]
    assert da["employment_type"] == "contract" and da["salary_min"] is None, "hourly pay isn't a yearly salary"
    assert {s["name"]: s["required"] for s in da["skills"]}.get("Excel") is False


# ---------------------------------------------------------------- adzuna + duplicates
def test_adzuna_needs_keys(empty):
    configure(empty, "adzuna", ["data engineer"])
    run = run_source("adzuna", empty, FakeHttp({}))
    assert run["status"] == "failed" and "ADZUNA_APP_ID" in run["errors"][0]["error"]


def test_adzuna_and_cross_source_duplicates(empty, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "adzuna_app_id", "id")
    monkeypatch.setattr(get_settings(), "adzuna_app_key", "key")
    configure(empty, "greenhouse", ["exampleco"])
    run_source("greenhouse", empty, gh_http())
    configure(empty, "adzuna", ["data engineer"])
    http = FakeHttp({AZ: load_json("adzuna_search.json")})
    run = run_source("adzuna", empty, http)
    assert http.calls[0][1]["where"] == "Edmonton", "searched in your profile's location"
    assert http.calls[0][1]["app_key"] == "key"
    assert (run["inserted"], run["skipped"]) == (1, 1), "the Data Engineer job is already in from Greenhouse"
    (bi,) = jobs(empty, "adzuna")
    assert bi["title"] == "BI Developer" and bi["salary_min"] == 78000 and bi["salary_currency"] == "CAD"


def test_adzuna_never_stores_predicted_salaries(empty, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "adzuna_app_id", "id")
    monkeypatch.setattr(get_settings(), "adzuna_app_key", "key")
    configure(empty, "adzuna", ["data engineer"])
    run_source("adzuna", empty, FakeHttp({AZ: load_json("adzuna_search.json")}))
    de = next(j for j in jobs(empty, "adzuna") if j["source_job_id"] == "4000000001")
    assert de["salary_min"] is None and de["title"] == "Data Engineer"


# ---------------------------------------------------------------- the API and settings
def test_runs_show_in_settings_and_api(empty_client, empty, monkeypatch):
    import app.routers.ingestion as ingestion

    configure(empty, "greenhouse", ["exampleco"])
    monkeypatch.setattr(ingestion, "run_source", lambda source: run_source(source, empty, gh_http()))
    response = empty_client.post("/api/v1/ingestion/runs", params={"source": "greenhouse"})
    assert response.status_code == 200, response.text
    assert response.json()[0]["inserted"] == 2
    gh = empty_client.get("/api/v1/settings").json()["sources"][0]
    assert gh["last_run_status"] == "partial" and gh["last_run_summary"]["inserted"] == 2
    assert empty_client.get("/api/v1/ingestion/runs").json()[0]["source"] == "greenhouse"
    page = empty_client.get("/api/v1/jobs").json()
    assert page["total"] == 2 and page["items"][0]["match"] is not None


# ---------------------------------------------------------------- helpers
def test_html_to_text():
    assert html_to_text("<p>Hi&nbsp;<b>there</b></p><ul><li>One</li><li>Two</li></ul>") == "Hi there\n\n- One\n- Two"
    assert html_to_text("<style>p{}</style><p>x</p>") == "x"
    assert html_to_text(None) == ""


@pytest.mark.parametrize(
    "text, expected",
    [("Full-time", "full_time"), ("Part Time", "part_time"), ("Contract", "contract"),
     ("Intern", "internship"), ("Temporary", "temporary"), (None, "unknown")],
)  # fmt: skip
def test_employment_type(text, expected):
    assert detect_employment_type(text) == expected


def test_skills_need_whole_words():
    found = {s["name"] for s in extract_skills("We go to the gym and use GitLab. Using C# and R for stats.")}
    assert "Go" not in found and "Git" not in found
    assert "C#" in found and "R" in found
