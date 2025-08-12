from fastapi.testclient import TestClient


def test_healthz_returns_ok() -> None:
    from apps.api.main import app

    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
