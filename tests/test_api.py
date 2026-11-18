"""API foundation tests ensuring Phase 1 endpoints remain intact."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "AI Website Link Analysis API",
        "version": "1.0.0",
        "status": "running",
    }


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_swagger_docs_load():
    response = client.get("/docs")
    assert response.status_code == 200
    assert "AI Website Link Analysis API" in response.text


def test_openapi_schema_metadata_and_routes():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "AI Website Link Analysis API"
    assert data["info"]["version"] == "1.0.0"
    assert "/" in data["paths"]
    assert "/health" in data["paths"]
    assert "/link-analysis" not in data["paths"]

