"""Step 1: the API runs and the website is allowed to call it."""

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
