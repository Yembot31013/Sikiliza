from fastapi.testclient import TestClient

from app.main import create_app


def test_health_reports_configuration() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "provider" in body
    assert "mode" in body
    assert "configured" in body
