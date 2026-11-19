"""
Steps 2b to 2d: the jobs endpoints. Read a failing test's name and message
first; each one checks a single rule from the docstrings in app/routers/jobs.py.

Expected results are worked out from db/seed/jobs.json, so if you change the
sample data these tests still hold.
"""

import pytest

from tests.conftest import parse_time

# The fields the website requires in every job (frontend/js/api/contract.js).
CONTRACT_FIELDS = [
    "id", "source", "source_job_id", "title", "company", "location",
    "work_arrangement", "employment_type", "description", "url",
    "salary_min", "salary_max", "salary_currency",
    "posted_at", "first_seen_at", "last_seen_at",
    "review_status", "skills", "match", "application_id",
]  # fmt: skip


def ids(page):
    return [job["id"] for job in page["items"]]


def list_jobs(client, **params):
    response = client.get("/api/v1/jobs", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def everything(client, **params):
    return list_jobs(client, review_status="all", limit=100, **params)


def score(job):
    return (job["match"] or {}).get("score", -1)


# ---------------------------------------------------------------- 2b: one job


def test_get_one_job(client, seed_jobs):
    expected = seed_jobs[0]
    response = client.get(f"/api/v1/jobs/{expected['id']}")
    assert response.status_code == 200, response.text
    job = response.json()
    assert job["id"] == expected["id"]
    assert job["title"] == expected["title"]
    assert job["company"] == expected["company"]
    assert job["skills"] == expected["skills"]
    assert job["match"]["score"] == expected["match"]["score"]
    assert job["application_id"] is None


def test_job_has_every_field_the_website_needs(client, seed_jobs):
    job = client.get(f"/api/v1/jobs/{seed_jobs[0]['id']}").json()
    missing = [field for field in CONTRACT_FIELDS if field not in job]
    assert not missing, f"missing fields: {missing}"


def test_job_without_location_comes_back_as_null(client, seed_jobs):
    remote = next(j for j in seed_jobs if j["location"] is None)
    assert client.get(f"/api/v1/jobs/{remote['id']}").json()["location"] is None


def test_unknown_job_is_404(client):
    response = client.get("/api/v1/jobs/job_nope")
    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}


# ---------------------------------------------------------------- 2c: the list


def test_list_shape(client):
    page = list_jobs(client)
    assert set(page) == {"items", "total", "limit", "offset"}
    assert page["limit"] == 20 and page["offset"] == 0
    for job in page["items"]:
        missing = [field for field in CONTRACT_FIELDS if field not in job]
        assert not missing, f"{job.get('id')} is missing {missing}"


def test_default_is_active_jobs_best_match_first(client, seed_jobs):
    page = list_jobs(client)
    active = [j for j in seed_jobs if j["review_status"] != "dismissed"]
    assert page["total"] == len(active)
    assert all(job["review_status"] in ("new", "shortlisted") for job in page["items"])
    scores = [score(job) for job in page["items"]]
    assert scores == sorted(scores, reverse=True), "sort=match: highest score first"


def test_match_ties_are_broken_by_newest(client):
    items = everything(client, sort="match")["items"]
    for a, b in zip(items, items[1:]):
        if score(a) == score(b):
            assert parse_time(a["first_seen_at"]) >= parse_time(b["first_seen_at"]), (
                f"{a['id']} and {b['id']} have the same score; the newer one comes first"
            )


@pytest.mark.parametrize("status", ["new", "shortlisted", "dismissed"])
def test_filter_by_review_status(client, seed_jobs, status):
    page = list_jobs(client, review_status=status, limit=100)
    assert sorted(ids(page)) == sorted(j["id"] for j in seed_jobs if j["review_status"] == status)


def test_review_status_all(client, seed_jobs):
    assert everything(client)["total"] == len(seed_jobs)


def test_bad_review_status_is_422(client):
    assert client.get("/api/v1/jobs", params={"review_status": "maybe"}).status_code == 422


def test_search_title_ignores_case(client, seed_jobs):
    page = everything(client, q="DATA ENGINEER")
    expected = [j["id"] for j in seed_jobs if "data engineer" in j["title"].lower()]
    assert sorted(ids(page)) == sorted(expected)
    assert page["total"] == len(expected)


def test_search_company(client, seed_jobs):
    page = everything(client, company="kestrel")
    expected = [j["id"] for j in seed_jobs if "kestrel" in j["company"]["name"].lower()]
    assert expected, "the sample data should have Kestrel jobs"
    assert sorted(ids(page)) == sorted(expected)


def test_search_location(client, seed_jobs):
    page = everything(client, location="calgary")
    expected = [j["id"] for j in seed_jobs if "calgary" in (j["location"] or "").lower()]
    assert sorted(ids(page)) == sorted(expected)


def test_location_remote_includes_remote_jobs(client, seed_jobs):
    page = everything(client, location="Remote")
    expected = [
        j["id"]
        for j in seed_jobs
        if j["work_arrangement"] == "remote" or "remote" in (j["location"] or "").lower()
    ]
    assert sorted(ids(page)) == sorted(expected), "remote jobs often have no location; match them anyway"


def test_filter_by_source(client, seed_jobs):
    page = everything(client, source="lever")
    assert sorted(ids(page)) == sorted(j["id"] for j in seed_jobs if j["source"] == "lever")


def test_bad_source_is_422(client):
    assert client.get("/api/v1/jobs", params={"source": "linkedin"}).status_code == 422


def test_min_score(client, seed_jobs):
    page = everything(client, min_score=90)
    expected = [j["id"] for j in seed_jobs if j["match"] and j["match"]["score"] >= 90]
    assert sorted(ids(page)) == sorted(expected)


def test_min_score_out_of_range_is_422(client):
    assert client.get("/api/v1/jobs", params={"min_score": 101}).status_code == 422


def test_found_after(client):
    all_jobs = everything(client, sort="newest")["items"]
    cutoff = all_jobs[4]["first_seen_at"]  # the 5th newest
    page = everything(client, found_after=cutoff)
    expected = [j["id"] for j in all_jobs if parse_time(j["first_seen_at"]) >= parse_time(cutoff)]
    assert sorted(ids(page)) == sorted(expected)


def test_filters_combine(client, seed_jobs):
    page = everything(client, q="data", location="edmonton", min_score=80)
    expected = [
        j["id"]
        for j in seed_jobs
        if "data" in j["title"].lower()
        and "edmonton" in (j["location"] or "").lower()
        and j["match"]["score"] >= 80
    ]
    assert sorted(ids(page)) == sorted(expected)


def test_sort_newest(client):
    items = everything(client, sort="newest")["items"]
    times = [parse_time(j["first_seen_at"]) for j in items]
    assert times == sorted(times, reverse=True)


def test_sort_posted(client):
    items = everything(client, sort="posted")["items"]
    dated = [parse_time(j["posted_at"]) for j in items if j["posted_at"]]
    assert dated == sorted(dated, reverse=True)
    # jobs with no posted date come last
    seen_null = False
    for job in items:
        if job["posted_at"] is None:
            seen_null = True
        else:
            assert not seen_null, "jobs without posted_at belong at the end"


def test_pagination(client, seed_jobs):
    full = everything(client, sort="newest")
    first = list_jobs(client, review_status="all", sort="newest", limit=5, offset=0)
    second = list_jobs(client, review_status="all", sort="newest", limit=5, offset=5)
    assert first["total"] == second["total"] == len(seed_jobs), "total counts all matches, not one page"
    assert len(first["items"]) == len(second["items"]) == 5
    assert ids(first) + ids(second) == ids(full)[:10]
    assert second["limit"] == 5 and second["offset"] == 5


def test_page_past_the_end_is_empty(client, seed_jobs):
    page = list_jobs(client, review_status="all", offset=500)
    assert page["items"] == [] and page["total"] == len(seed_jobs)


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_bad_paging_is_422(client, params):
    assert client.get("/api/v1/jobs", params=params).status_code == 422


def test_no_matches_is_an_empty_page(client):
    page = everything(client, q="astronaut")
    assert page["items"] == [] and page["total"] == 0


def test_search_text_is_never_run_as_sql(client, seed_jobs):
    """If this fails, user input is being pasted into the SQL. Use %s placeholders."""
    attacks = ["' OR '1'='1", "'; DROP TABLE jobs; --", "%", "_"]
    for text in attacks:
        response = client.get("/api/v1/jobs", params={"q": text, "review_status": "all"})
        assert response.status_code == 200, f"q={text!r} broke the query: {response.text}"
        assert response.json()["total"] == 0, f"q={text!r} should match nothing"
    assert everything(client)["total"] == len(seed_jobs), "the jobs table must still be there"


# ---------------------------------------------------------------- 2d: status


def test_update_shortlists_a_job(client, db, seed_jobs):
    job = next(j for j in seed_jobs if j["review_status"] == "new")
    response = client.patch(f"/api/v1/jobs/{job['id']}", json={"review_status": "shortlisted"})
    assert response.status_code == 200, response.text
    assert response.json()["review_status"] == "shortlisted"
    assert response.json()["id"] == job["id"]
    stored = db.execute("SELECT review_status FROM jobs WHERE id = %s", (job["id"],)).fetchone()
    assert stored["review_status"] == "shortlisted", "the change must be saved in the database"


def test_update_dismissed_job_leaves_the_active_list(client, seed_jobs):
    job = next(j for j in seed_jobs if j["review_status"] == "new")
    client.patch(f"/api/v1/jobs/{job['id']}", json={"review_status": "dismissed"})
    assert job["id"] not in ids(list_jobs(client, limit=100))
    client.patch(f"/api/v1/jobs/{job['id']}", json={"review_status": "new"})
    assert job["id"] in ids(list_jobs(client, limit=100))


def test_update_only_changes_that_job(client, db, seed_jobs):
    job = next(j for j in seed_jobs if j["review_status"] == "new")
    client.patch(f"/api/v1/jobs/{job['id']}", json={"review_status": "dismissed"})
    dismissed = db.execute("SELECT count(*) AS n FROM jobs WHERE review_status = 'dismissed'").fetchone()["n"]
    assert dismissed == sum(1 for j in seed_jobs if j["review_status"] == "dismissed") + 1


def test_update_bad_status_is_422(client, seed_jobs):
    response = client.patch(f"/api/v1/jobs/{seed_jobs[0]['id']}", json={"review_status": "applied"})
    assert response.status_code == 422


def test_update_unknown_job_is_404(client):
    response = client.patch("/api/v1/jobs/job_nope", json={"review_status": "shortlisted"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found"}
