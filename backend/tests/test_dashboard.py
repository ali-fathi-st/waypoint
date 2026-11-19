"""Dashboard numbers, checked against the definitions in docs/06 worked out in Python."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tests.conftest import contract_fields

TZ = ZoneInfo("America/Edmonton")
SUBMITTED = {"applied", "interview", "offer", "rejected"}


def expected_counts(apps):
    def reached(a):
        return a["status"] in ("interview", "offer") or any(
            e["to_status"] == "interview" or e["event_type"] == "interview_scheduled" for e in a["events"]
        )

    submitted = [a for a in apps if a["status"] in SUBMITTED or (a["status"] == "withdrawn" and a["applied_at"])]
    responses = [a for a in submitted if reached(a) or a["status"] in ("offer", "rejected")]
    today = datetime.now(TZ).date().isoformat()
    return {
        "applications_submitted": len(submitted),
        "interviews": sum(1 for a in apps if reached(a)),
        "responses": len(responses),
        "follow_ups_due": sum(
            1 for a in apps if a["status"] in ("applied", "interview") and a["follow_up_at"] and a["follow_up_at"] <= today
        ),
    }


def test_metrics(client, demo):
    m = client.get("/api/v1/dashboard/metrics").json()
    assert not [f for f in contract_fields()["metrics"] if f not in m]
    assert {k: m[k] for k in expected_counts(demo["applications"])} == expected_counts(demo["applications"])
    assert m["total_jobs"] == len(demo["jobs"])
    assert m["shortlisted_jobs"] == sum(1 for j in demo["jobs"] if j["review_status"] == "shortlisted")
    assert abs(m["response_rate"] - m["responses"] / m["applications_submitted"]) < 1e-9


def test_jobs_by_day_is_14_days_oldest_first_with_zeros(client, demo):
    days = client.get("/api/v1/dashboard/metrics").json()["jobs_found_by_day"]
    today = datetime.now(TZ).date()
    assert [d["date"] for d in days] == [str(today - timedelta(days=13 - i)) for i in range(14)]
    for day in days:
        expected = sum(
            1 for j in demo["jobs"]
            if datetime.fromisoformat(j["first_seen_at"]).astimezone(TZ).date().isoformat() == day["date"]
        )  # fmt: skip
        assert day["count"] == expected, day["date"]


def test_jobs_to_review_are_the_best_new_ones(client):
    m = client.get("/api/v1/dashboard/metrics").json()
    review = m["jobs_to_review"]
    assert len(review) <= 5 and all(j["review_status"] == "new" for j in review)
    scores = [j["match"]["score"] for j in review]
    assert scores == sorted(scores, reverse=True)


def test_recent_activity(client):
    activity = client.get("/api/v1/dashboard/metrics").json()["recent_activity"]
    assert len(activity) == 8
    assert all(a["job_title"] and a["company_name"] for a in activity)
    times = [a["occurred_at"] for a in activity]
    assert times == sorted(times, reverse=True)


def test_empty_database(empty_client):
    m = empty_client.get("/api/v1/dashboard/metrics").json()
    assert m["total_jobs"] == 0 and m["response_rate"] is None and m["recent_activity"] == []
    assert len(m["jobs_found_by_day"]) == 14 and all(d["count"] == 0 for d in m["jobs_found_by_day"])
