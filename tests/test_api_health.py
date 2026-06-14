from fastapi.testclient import TestClient

from api.server import app


def test_health_endpoint_reports_components():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "degraded")
    assert body["components"]["api"] == "ok"
    assert "ollama" in body["components"]
