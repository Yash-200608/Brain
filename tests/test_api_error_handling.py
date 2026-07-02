"""An unhandled exception anywhere downstream of a route (e.g. a
ModelProviderError when Ollama is unreachable) must still produce a
readable, CORS-headered JSON response -- not an opaque failure a
cross-origin caller (the dashboard) can't distinguish from a CORS or
auth problem. Found via real end-to-end verification of the dashboard
auth restoration, not asserted from first principles.
"""
from fastapi.testclient import TestClient

from api.server import app
from identity import IdentityService, set_identity_service


def teardown_function():
    set_identity_service(None)


def test_unhandled_exception_returns_readable_cors_headered_500(monkeypatch):
    set_identity_service(IdentityService(api_keys={"tok": "owner"}))

    from api.routes import query as query_route

    class ExplodingOrchestrator:
        def handle(self, *args, **kwargs):
            raise RuntimeError("simulated downstream failure (e.g. Ollama unreachable)")

    monkeypatch.setattr(query_route, "_orch", ExplodingOrchestrator())

    client = TestClient(app, raise_server_exceptions=False)
    origin = "http://localhost:5173"
    r = client.post(
        "/api/query",
        headers={"Origin": origin, "Authorization": "Bearer tok"},
        json={"query": "hello", "session_id": None},
    )

    assert r.status_code == 500
    assert r.json()["error"] == "internal_error"
    assert "simulated downstream failure" in r.json()["detail"]
    # The core regression: CORS headers must be present on error responses
    # too, or a cross-origin caller sees an opaque network failure instead
    # of this readable body.
    assert r.headers.get("access-control-allow-origin") == origin
