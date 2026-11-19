"""The Python match score gives exactly what the website's JavaScript version gives."""

from datetime import datetime, timezone

from app.services.matching import WEIGHTS, _js_round, score_job

NOW = datetime(2026, 11, 19, tzinfo=timezone.utc)


def test_same_scores_as_the_javascript_version(demo):
    for job in demo["jobs"]:
        expected = job["match"]
        actual = score_job(job, demo["profile"], NOW)
        assert actual["score"] == expected["score"], job["id"]
        assert actual["summary"] == expected["summary"], job["id"]
        assert actual["factors"] == expected["factors"], job["id"]
        assert actual["matched_skills"] == expected["matched_skills"], job["id"]
        assert actual["missing_skills"] == expected["missing_skills"], job["id"]


def test_weights_add_up_to_one():
    assert abs(sum(WEIGHTS.values()) - 1) < 1e-9


def test_rounds_halves_up_like_javascript():
    assert _js_round(84.5) == 85
    assert _js_round(84.4999) == 84


def test_excluded_words_zero_the_title(demo):
    job = {**demo["jobs"][0], "title": "Senior Data Engineer"}
    title = next(f for f in score_job(job, demo["profile"], NOW)["factors"] if f["key"] == "title")
    assert title["score"] == 0 and "exclusion" in title["detail"]


def test_empty_profile_still_scores():
    profile = {"skills": [], "preferred_titles": [], "exclusions": [], "locations": [], "work_arrangements": [],
               "salary_min": None}  # fmt: skip
    job = {"id": "j", "title": "Anything", "skills": [], "location": None, "work_arrangement": "unknown",
           "salary_max": None}  # fmt: skip
    match = score_job(job, profile, NOW)
    assert 0 <= match["score"] <= 100
