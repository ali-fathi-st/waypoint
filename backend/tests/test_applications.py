"""
Applications and every rule in docs/06. Ported from tests/mock-api.test.js
(the website's mock follows the same rules), plus the server-only checks.
"""

from datetime import timedelta

import pytest

from app.util import today_in
from tests.conftest import contract_fields

APPS = "/api/v1/applications"
TODAY = today_in("America/Edmonton")


def free_job(client) -> dict:
    jobs = client.get("/api/v1/jobs", params={"review_status": "all", "limit": 100}).json()["items"]
    return next(j for j in jobs if not j["application_id"] and j["review_status"] == "new")


def new_app(client, **body) -> dict:
    response = client.post(APPS, json={"job_id": free_job(client)["id"], **body})
    assert response.status_code == 201, response.text
    return response.json()


def confirm(client, app_id, **changes):
    body = {"applied_at": str(TODAY), "follow_up_at": str(TODAY + timedelta(days=14)),
            "resume_document_id": "doc_003", "cover_letter_document_id": None, **changes}  # fmt: skip
    return client.post(f"{APPS}/{app_id}/confirm-submission", json=body)


def field_error(response, field):
    detail = response.json()["detail"]
    return isinstance(detail, list) and any(d["loc"][-1] == field for d in detail)


# ---------------------------------------------------------------- reading
def test_list_has_every_field_and_newest_change_first(client, demo):
    apps = client.get(APPS).json()
    assert len(apps) == len(demo["applications"])
    required = contract_fields()["application"]
    for app in apps:
        assert not [f for f in required if f not in app], app["id"]
    times = [a["updated_at"] for a in apps]
    assert times == sorted(times, reverse=True)


def test_filter_by_status_and_search(client):
    applied = client.get(APPS, params={"status": "applied"}).json()
    assert applied and all(a["status"] == "applied" for a in applied)
    found = client.get(APPS, params={"q": "ravine"}).json()
    assert found and all("ravine" in a["job"]["company_name"].lower() for a in found)


def test_events_newest_first(client):
    app = client.get(f"{APPS}/app_005").json()
    times = [e["occurred_at"] for e in app["events"]]
    assert times == sorted(times, reverse=True)
    assert any(e["event_type"] == "interview_scheduled" and e["interview"] for e in app["events"])


def test_unknown_application_is_404(client):
    assert client.get(f"{APPS}/nope").status_code == 404


# ---------------------------------------------------------------- creating
def test_create_shortlists_a_new_job_and_links_it(client):
    job = free_job(client)
    app = client.post(APPS, json={"job_id": job["id"], "notes": "Looks good"}).json()
    assert app["status"] == "saved" and app["status_source"] == "user" and app["notes"] == "Looks good"
    assert [e["event_type"] for e in app["events"]] == ["created"]
    after = client.get(f"/api/v1/jobs/{job['id']}").json()
    assert after["application_id"] == app["id"] and after["review_status"] == "shortlisted"


def test_one_application_per_job(client):
    app = new_app(client)
    again = client.post(APPS, json={"job_id": app["job_id"]})
    assert again.status_code == 409


def test_create_for_unknown_job_is_404(client):
    assert client.post(APPS, json={"job_id": "job_nope"}).status_code == 404


# ---------------------------------------------------------------- status
def test_applied_only_through_confirm_submission(client):
    app = new_app(client)
    assert client.patch(f"{APPS}/{app['id']}", json={"status": "applied"}).status_code == 422


def test_moves_that_skip_steps_are_refused(client):
    app = new_app(client)
    response = client.patch(f"{APPS}/{app['id']}", json={"status": "offer"})
    assert response.status_code == 422 and field_error(response, "status")


def test_allowed_move_writes_an_event(client):
    app = new_app(client)
    moved = client.patch(f"{APPS}/{app['id']}", json={"status": "preparing"}).json()
    assert moved["status"] == "preparing"
    event = moved["events"][0]
    assert (event["event_type"], event["from_status"], event["to_status"]) == ("status_changed", "saved", "preparing")
    assert event["summary"] == "Status changed to preparing"


def test_closed_stays_closed(client):
    app = new_app(client)
    client.patch(f"{APPS}/{app['id']}", json={"status": "withdrawn"})
    assert client.patch(f"{APPS}/{app['id']}", json={"status": "saved"}).status_code == 422


def test_same_status_is_not_a_change(client):
    app = new_app(client)
    same = client.patch(f"{APPS}/{app['id']}", json={"status": "saved"}).json()
    assert len(same["events"]) == 1


# ---------------------------------------------------------------- confirm submission
def test_confirm_sets_date_follow_up_and_history(client):
    app = new_app(client)
    done = confirm(client, app["id"]).json()
    assert done["status"] == "applied"
    assert done["applied_at"] == str(TODAY)
    assert done["follow_up_at"] == str(TODAY + timedelta(days=14))
    assert done["resume_document_id"] == "doc_003"
    types = [e["event_type"] for e in done["events"]]
    assert "submission_confirmed" in types and "follow_up_set" in types


def test_future_application_date_is_refused(client):
    app = new_app(client)
    response = confirm(client, app["id"], applied_at=str(TODAY + timedelta(days=1)), follow_up_at=None)
    assert response.status_code == 422 and field_error(response, "applied_at")


def test_follow_up_before_applying_is_refused(client):
    app = new_app(client)
    response = confirm(client, app["id"], follow_up_at=str(TODAY - timedelta(days=1)))
    assert response.status_code == 422 and field_error(response, "follow_up_at")


def test_confirm_twice_is_refused(client):
    app = new_app(client)
    confirm(client, app["id"])
    assert confirm(client, app["id"]).status_code == 422


def test_cover_letter_cant_be_linked_as_resume(client):
    app = new_app(client)
    response = confirm(client, app["id"], resume_document_id="doc_004")
    assert response.status_code == 422 and field_error(response, "resume_document_id")


def test_unknown_document_is_refused(client):
    app = new_app(client)
    response = client.patch(f"{APPS}/{app['id']}", json={"resume_document_id": "doc_nope"})
    assert response.status_code == 422


# ---------------------------------------------------------------- follow-ups
def test_closing_clears_the_follow_up(client):
    applied = client.get(APPS, params={"status": "applied"}).json()
    app = next(a for a in applied if a["follow_up_at"])
    closed = client.patch(f"{APPS}/{app['id']}", json={"status": "rejected"}).json()
    assert closed["follow_up_at"] is None
    assert any(e["summary"].startswith("Follow-up cleared") for e in closed["events"])


def test_follow_up_only_for_open_applications(client):
    app = new_app(client)
    response = client.patch(f"{APPS}/{app['id']}", json={"follow_up_at": str(TODAY)})
    assert response.status_code == 422 and field_error(response, "follow_up_at")


def test_change_and_clear_follow_up(client):
    app = new_app(client)
    confirm(client, app["id"])
    later = TODAY + timedelta(days=20)
    changed = client.patch(f"{APPS}/{app['id']}", json={"follow_up_at": str(later)}).json()
    assert changed["follow_up_at"] == str(later)
    assert changed["events"][0]["summary"] == f"Follow-up set for {later:%b} {later.day}, {later.year}"
    cleared = client.patch(f"{APPS}/{app['id']}", json={"follow_up_at": None}).json()
    assert cleared["follow_up_at"] is None and cleared["events"][0]["summary"] == "Follow-up cleared"


def test_notes_only_change_what_is_sent(client):
    app = new_app(client)
    confirm(client, app["id"])
    noted = client.patch(f"{APPS}/{app['id']}", json={"notes": "Called the recruiter"}).json()
    assert noted["notes"] == "Called the recruiter"
    assert noted["follow_up_at"] is not None, "a field that wasn't sent must not change"
    assert noted["events"][0]["event_type"] == "note_updated"


def test_notes_have_a_limit(client):
    app = new_app(client)
    assert client.patch(f"{APPS}/{app['id']}", json={"notes": "x" * 5001}).status_code == 422


# ---------------------------------------------------------------- interviews
def test_interview_moves_applied_to_interview(client):
    app = new_app(client)
    confirm(client, app["id"])
    body = {"scheduled_for": "2026-12-01T16:00:00Z", "format": "onsite", "with_whom": "Team lead"}
    updated = client.post(f"{APPS}/{app['id']}/interviews", json=body).json()
    assert updated["status"] == "interview"
    event = updated["events"][0]
    assert event["event_type"] == "interview_scheduled" and event["summary"] == "On-site interview scheduled"
    assert event["interview"]["with_whom"] == "Team lead"
    assert updated["follow_up_at"] is not None, "interviewing keeps the follow-up"


def test_interview_needs_an_applied_application(client):
    app = new_app(client)
    body = {"scheduled_for": "2026-12-01T16:00:00Z", "format": "video"}
    assert client.post(f"{APPS}/{app['id']}/interviews", json=body).status_code == 422


@pytest.mark.parametrize("body", [{"scheduled_for": "soon", "format": "video"},
                                  {"scheduled_for": "2026-12-01T16:00:00Z", "format": "carrier pigeon"}])  # fmt: skip
def test_interview_input_is_validated(client, body):
    app = new_app(client)
    confirm(client, app["id"])
    assert client.post(f"{APPS}/{app['id']}/interviews", json=body).status_code == 422


def test_deleting_isnt_possible(client):
    """Applications are a history; withdraw or archive instead. There's no DELETE."""
    assert client.delete(f"{APPS}/app_001").status_code == 405


def test_failed_rule_changes_nothing(client, db):
    """A request that fails part-way must leave no half-written change."""
    app = new_app(client)
    # notes are saved first, then the follow-up fails: the notes must be rolled back too
    response = client.patch(f"{APPS}/{app['id']}", json={"notes": "first", "follow_up_at": str(TODAY)})
    assert response.status_code == 422
    row = db.execute("SELECT notes, status FROM applications WHERE id = %s", (app["id"],)).fetchone()
    assert row == {"notes": "", "status": "saved"}
    assert len(client.get(f"{APPS}/{app['id']}").json()["events"]) == 1
