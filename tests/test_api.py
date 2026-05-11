from fastapi.testclient import TestClient

from app.main import app


def test_root_lists_core_routes():
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["health"] == "/healthz"
    assert payload["optimize"] == "POST /optimize"
    assert payload["fresh"] == "POST /fresh"


def test_healthz():
    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
