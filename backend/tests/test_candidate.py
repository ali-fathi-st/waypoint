"""The candidate profile, and re-scoring when it changes."""

from tests.conftest import contract_fields

URL = "/api/v1/candidate"


def profile_input(client) -> dict:
    p = client.get(URL).json()
    return {k: v for k, v in p.items() if k not in ("id", "updated_at")}


def test_get_matches_the_demo(client, demo):
    p = client.get(URL).json()
    assert not [f for f in contract_fields()["profile"] if f not in p]
    assert p["full_name"] == demo["profile"]["full_name"]
    assert [s["name"] for s in p["skills"]] == [s["name"] for s in demo["profile"]["skills"]]
    assert p["skills"][0]["years"] == demo["profile"]["skills"][0]["years"]
    assert p["experience"][0]["end_month"] is None


def test_put_round_trip(client):
    body = profile_input(client)
    body["headline"] = "Data engineer"
    body["experience"].append(
        {"title": "Analyst", "company": "Somewhere", "start_month": "2020-01", "end_month": "2021-06", "description": ""}
    )
    saved = client.put(URL, json=body)
    assert saved.status_code == 200, saved.text
    p = saved.json()
    assert p["headline"] == "Data engineer"
    assert p["experience"][-1]["id"], "new rows get an id"
    assert client.get(URL).json() == p


def test_saving_rescores_jobs(client):
    before = client.get("/api/v1/jobs/job_002").json()["match"]
    body = profile_input(client)
    body["skills"].append({"name": "dbt", "proficiency": "familiar", "years": 1})
    client.put(URL, json=body)
    after = client.get("/api/v1/jobs/job_002").json()["match"]
    assert "dbt" not in before["matched_skills"] and "dbt" in after["matched_skills"]
    assert after["score"] > before["score"]


def test_lists_are_cleaned(client):
    body = profile_input(client)
    body["preferred_titles"] = [" Data Engineer ", "data engineer", "", "BI Developer"]
    p = client.put(URL, json=body).json()
    assert p["preferred_titles"] == ["Data Engineer", "BI Developer"]


def test_validation(client):
    body = profile_input(client)
    assert client.put(URL, json={**body, "salary_min": 100, "salary_max": 50}).status_code == 422
    assert client.put(URL, json={**body, "work_arrangements": ["moon"]}).status_code == 422
    dup = body["skills"] + [{"name": body["skills"][0]["name"].upper(), "proficiency": "expert", "years": 1}]
    assert client.put(URL, json={**body, "skills": dup}).status_code == 422
    bad_month = [{"title": "T", "company": "C", "start_month": "2020-13"}]
    assert client.put(URL, json={**body, "experience": bad_month}).status_code == 422


def test_empty_install_has_a_blank_profile(empty_client):
    p = empty_client.get(URL).json()
    assert p["full_name"] == "" and p["skills"] == []
