"""
The match score: a Python port of scoreJob() in frontend/js/data/sample-data.js.

Each factor scores 0-1 and has a fixed weight (the weights add up to 1). The
job's score is round(sum of weight x score x 100). Every factor carries a
one-line explanation, which the job page shows. No AI: it's transparent rules,
so you can always see why a job scored what it did.

tests/test_matching.py checks this gives exactly the same numbers as the
JavaScript version.
"""

import math
import re
from datetime import datetime

from psycopg.types.json import Jsonb

from app.services.area import remote_open_to_you, user_area

WEIGHTS = {
    "required_skills": 0.4,
    "preferred_skills": 0.15,
    "title": 0.2,
    "location": 0.1,
    "work_arrangement": 0.1,
    "salary": 0.05,
}


def _norm(text: str) -> str:
    return text.strip().lower()


def _js_round(value: float) -> int:
    """JavaScript's Math.round (halves go up). Python's round() would give 84 for 84.5."""
    return math.floor(value + 0.5)


def _city(location: str) -> str:
    return _norm(location.split(",")[0])


def score_job(job: dict, profile: dict, now: datetime) -> dict:
    """
    job:     needs id, title, skills, location, work_arrangement, salary_max
    profile: needs skills, preferred_titles, exclusions, locations,
             work_arrangements, salary_min
    Returns the `match` object stored on the job.
    """
    mine = {_norm(s["name"]) for s in profile["skills"]}
    required = [s for s in job["skills"] if s["required"]]
    preferred = [s for s in job["skills"] if not s["required"]]

    def has(skill):
        return _norm(skill["name"]) in mine

    req_matched = [s for s in required if has(s)]
    pref_matched = [s for s in preferred if has(s)]
    factors = []

    # A posting with no skills found at all says nothing either way: half marks, not full.
    unknown = not job["skills"]
    factors.append({
        "key": "required_skills",
        "label": "Required skills",
        "weight": WEIGHTS["required_skills"],
        "score": 0.5 if unknown else len(req_matched) / len(required) if required else 1,
        "detail": "No skills found in the posting" if unknown
        else f"{len(req_matched)} of {len(required)} required skills on your profile"
        if required else "No required skills listed",
    })  # fmt: skip
    factors.append({
        "key": "preferred_skills",
        "label": "Nice-to-have skills",
        "weight": WEIGHTS["preferred_skills"],
        "score": 0.5 if unknown else len(pref_matched) / len(preferred) if preferred else 1,
        "detail": "No skills found in the posting" if unknown
        else f"{len(pref_matched)} of {len(preferred)} nice-to-have skills"
        if preferred else "No nice-to-have skills listed",
    })  # fmt: skip

    title = _norm(job["title"])
    title_words = re.split(r"[^A-Za-z0-9_]+", title)
    exact = next((t for t in profile["preferred_titles"] if _norm(t) in title), None)
    related = next(
        (t for t in profile["preferred_titles"] if any(len(w) > 3 and w in title_words for w in _norm(t).split())),
        None,
    )
    excluded = next((x for x in profile["exclusions"] if _norm(x) in title), None)
    if excluded:
        title_score, title_detail = 0, f'Contains "{excluded}", which is on your exclusion list'
    elif exact:
        title_score, title_detail = 1, f'Matches your target title "{exact}"'
    elif related:
        title_score, title_detail = 0.5, f'Related to your target title "{related}"'
    else:
        title_score, title_detail = 0, "Not one of your target titles"
    factors.append({"key": "title", "label": "Title", "weight": WEIGHTS["title"],
                    "score": title_score, "detail": title_detail})  # fmt: skip

    remote = job["work_arrangement"] == "remote"
    location = job["location"]
    remote_open = remote and remote_open_to_you(location, user_area(profile["locations"]))
    loc_match = remote_open or (
        location is not None and any(_city(mine_loc) == _city(location) for mine_loc in profile["locations"])
    )
    if remote_open:
        loc_detail = "Remote, so location doesn't limit you"
    elif remote and not loc_match:
        loc_detail = f"Remote, but only for people in {location}"
    elif loc_match:
        loc_detail = f"{location} is one of your locations"
    else:
        loc_detail = f"{location or 'Location not stated'} is outside your locations"
    factors.append({"key": "location", "label": "Location", "weight": WEIGHTS["location"],
                    "score": 1 if loc_match else 0, "detail": loc_detail})  # fmt: skip

    arrangement = job["work_arrangement"]
    arrangement_ok = arrangement != "unknown" and arrangement in profile["work_arrangements"]
    if arrangement == "unknown":
        arr_score, arr_detail = 0.5, "Arrangement not stated in the posting"
    elif arrangement_ok:
        arr_score, arr_detail = 1, "Matches a work arrangement you accept"
    else:
        arr_score, arr_detail = 0, "Not a work arrangement you selected"
    factors.append({"key": "work_arrangement", "label": "Work arrangement", "weight": WEIGHTS["work_arrangement"],
                    "score": arr_score, "detail": arr_detail})  # fmt: skip

    salary_score, salary_detail = 0.5, "Salary not posted"
    if job["salary_max"] is not None and profile["salary_min"] is not None:
        salary_score = 1 if job["salary_max"] >= profile["salary_min"] else 0
        salary_detail = (
            "Posted range reaches your minimum" if salary_score == 1 else "Posted range tops out below your minimum"
        )
    factors.append({"key": "salary", "label": "Salary", "weight": WEIGHTS["salary"],
                    "score": salary_score, "detail": salary_detail})  # fmt: skip

    total = 0.0
    for f in factors:  # same order as the JavaScript, so the floats match exactly
        total += f["weight"] * f["score"]
    missing_required = [s["name"] for s in required if not has(s)]
    n = len(missing_required)
    if unknown:
        summary = "No skills found in the posting; read it to judge the fit."
    elif n == 0:
        summary = "You have every required skill listed."
    else:
        summary = f"Missing {n} required skill{'' if n == 1 else 's'}: {', '.join(missing_required)}."
    return {
        "job_id": job["id"],
        "score": _js_round(total * 100),
        "summary": summary,
        "factors": factors,
        "matched_skills": [s["name"] for s in req_matched + pref_matched],
        "missing_skills": [s["name"] for s in required + preferred if not has(s)],
        "method": "rules",
        "computed_at": now.isoformat(),
    }


def load_profile_for_scoring(db) -> dict:
    row = db.execute(
        "SELECT preferred_titles, locations, work_arrangements, salary_min, exclusions FROM candidate_profile LIMIT 1"
    ).fetchone()
    skills = db.execute("SELECT name FROM candidate_skills ORDER BY position").fetchall()
    return {**row, "skills": skills}


def rescore(db, job_ids: list[str] | None = None, now: datetime | None = None) -> int:
    """Recompute and store the match for every job (or just job_ids). Returns how many."""
    from app.util import utc_now

    now = now or utc_now()
    profile = load_profile_for_scoring(db)
    query = "SELECT id, title, skills, location, work_arrangement, salary_max FROM jobs"
    params: tuple = ()
    if job_ids is not None:
        query += " WHERE id = ANY(%s)"
        params = (job_ids,)
    jobs = db.execute(query, params).fetchall()
    with db.cursor() as cur:
        cur.executemany(
            "UPDATE jobs SET match = %s, match_score = %s WHERE id = %s",
            [(Jsonb(m), m["score"], job["id"]) for job in jobs for m in [score_job(job, profile, now)]],
        )
    return len(jobs)
