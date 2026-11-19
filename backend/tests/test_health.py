"""The API runs, and only the listed websites may call it."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_says_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_the_local_website():
    response = client.get("/health", headers={"Origin": "http://localhost:8080"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:8080"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_ignores_unknown_websites():
    response = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_interactive_docs_exist():
    assert client.get("/docs").status_code == 200


def test_other_websites_cant_make_changes(client):
    response = client.post("/api/v1/ingestion/runs", headers={"Origin": "https://evil.example"})
    assert response.status_code == 403
    response = client.delete("/api/v1/data", headers={"Origin": "https://evil.example"})
    assert response.status_code == 403
    assert client.get("/api/v1/jobs").json()["total"] > 0, "nothing was deleted"


def test_the_website_and_scripts_can_make_changes(client):
    ok = client.patch("/api/v1/jobs/job_001", json={"review_status": "shortlisted"},
                      headers={"Origin": "http://localhost:8080"})  # fmt: skip
    assert ok.status_code == 200
    assert client.patch("/api/v1/jobs/job_001", json={"review_status": "new"}).status_code == 200


def test_unknown_host_names_are_refused():
    response = TestClient(app, base_url="http://rebind.example").get("/health")
    assert response.status_code == 400
