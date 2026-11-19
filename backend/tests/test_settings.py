"""Settings, export and delete-everything."""

from tests.conftest import contract_fields

URL = "/api/v1/settings"


def test_get(client):
    s = client.get(URL).json()
    assert not [f for f in contract_fields()["settings"] if f not in s]
    assert [x["source"] for x in s["sources"]] == ["greenhouse", "lever", "ashby", "rss", "adzuna"]
    lever = s["sources"][1]
    assert lever["last_run_status"] == "partial" and lever["last_run_summary"]["failed"] == 2


def test_credentials_are_never_returned(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "adzuna_app_id", "id-123")
    monkeypatch.setattr(get_settings(), "adzuna_app_key", "secret-456")
    body = client.get(URL).text
    assert "secret-456" not in body and "id-123" not in body
    adzuna = next(x for x in client.get(URL).json()["sources"] if x["source"] == "adzuna")
    assert adzuna["credentials_configured"] is True


def test_update_sources(client):
    change = {"source": "lever", "enabled": False, "identifiers": [" kestrel ", "kestrel", "new-co"]}
    s = client.patch(URL, json={"sources": [change]}).json()
    lever = next(x for x in s["sources"] if x["source"] == "lever")
    assert lever["enabled"] is False and lever["identifiers"] == ["kestrel", "new-co"]
    assert next(x for x in s["sources"] if x["source"] == "greenhouse")["enabled"] is True, "others unchanged"


def test_update_notifications_and_account(client):
    n = {"daily_digest": False, "digest_hour": 9, "digest_min_score": 80, "follow_up_reminders": False}
    assert client.patch(URL, json={"notifications": n}).json()["notifications"] == n
    a = {"display_name": "Ali", "email": "ali@example.com", "timezone": "America/Toronto"}
    assert client.patch(URL, json={"account": a}).json()["account"] == a


def test_bad_values(client):
    assert client.patch(URL, json={"account": {"display_name": "", "email": "", "timezone": "Mars/Base"}}).status_code == 422
    bad = {"daily_digest": True, "digest_hour": 25, "digest_min_score": 70, "follow_up_reminders": True}
    assert client.patch(URL, json={"notifications": bad}).status_code == 422
    assert client.patch(URL, json={"sources": [{"source": "linkedin", "enabled": True, "identifiers": []}]}).status_code == 422


def test_export(client, demo):
    response = client.get("/api/v1/export")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    data = response.json()
    assert len(data["jobs"]) == len(demo["jobs"]) and len(data["applications"]) == len(demo["applications"])
    assert data["profile"]["full_name"] == demo["profile"]["full_name"]


def test_delete_everything(client, private_storage):
    client.post(
        "/api/v1/documents",
        data={"document_type": "resume", "title": "R"},
        files={"file": ("r.pdf", b"%PDF-1.4 x", "application/pdf")},
    )
    assert any(private_storage.iterdir())
    assert client.delete("/api/v1/data").status_code == 204
    assert client.get("/api/v1/jobs", params={"review_status": "all"}).json()["total"] == 0
    assert client.get("/api/v1/applications").json() == []
    assert client.get("/api/v1/documents", params={"include_archived": "true"}).json() == []
    assert client.get("/api/v1/candidate").json()["full_name"] == ""
    s = client.get(URL).json()
    assert all(not x["enabled"] and x["last_run_status"] == "never" for x in s["sources"])
    assert not any(private_storage.iterdir()), "uploaded files are deleted too"
