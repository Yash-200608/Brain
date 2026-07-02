import asyncio

from starlette.requests import Request
from starlette.responses import PlainTextResponse

from api.middleware.auth import AuthMiddleware
from identity import IdentityService, Principal, set_identity_service


def _request(path: str = "/api/query", auth: str | None = None) -> Request:
    headers = [(b"authorization", auth.encode())] if auth else []
    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": headers,
        "client": ("1.2.3.4", 1234),
    }
    return Request(scope)


async def _ok(request: Request) -> PlainTextResponse:
    return PlainTextResponse(f"principal={request.state.principal.user_id}")


def teardown_function():
    set_identity_service(None)


def test_missing_credential_is_rejected_not_defaulted_to_owner():
    """The core regression: no Authorization header must be rejected, never
    silently resolved to the owner principal with full scopes."""
    set_identity_service(IdentityService(api_keys={}))
    mw = AuthMiddleware(None)
    response = asyncio.run(mw.dispatch(_request(auth=None), _ok))
    assert response.status_code == 401


def test_malformed_credential_is_rejected():
    set_identity_service(IdentityService(api_keys={"tok-alice": "alice"}))
    mw = AuthMiddleware(None)
    response = asyncio.run(mw.dispatch(_request(auth="NotBearer garbage"), _ok))
    assert response.status_code == 401


def test_unknown_token_is_rejected():
    set_identity_service(IdentityService(api_keys={"tok-alice": "alice"}))
    mw = AuthMiddleware(None)
    response = asyncio.run(mw.dispatch(_request(auth="Bearer does-not-exist"), _ok))
    assert response.status_code == 401


def test_valid_token_resolves_to_its_own_principal_not_owner():
    set_identity_service(IdentityService(api_keys={"tok-alice": "alice"}))
    mw = AuthMiddleware(None)
    response = asyncio.run(mw.dispatch(_request(auth="Bearer tok-alice"), _ok))
    assert response.status_code == 200
    assert response.body == b"principal=alice"


def test_health_path_is_exempt_even_without_credentials():
    # /health's real handler never touches request.state.principal (it's
    # simpler than the authenticated API routes) -- mirror that here rather
    # than reusing _ok, which requires a resolved principal.
    async def health_handler(request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    set_identity_service(IdentityService(api_keys={}))
    mw = AuthMiddleware(None)
    response = asyncio.run(mw.dispatch(_request(path="/health", auth=None), health_handler))
    assert response.status_code == 200


def test_options_preflight_is_exempt_even_without_credentials():
    """CORS preflight (OPTIONS) never carries credentials by browser design.
    AuthMiddleware sits outside CORSMiddleware in the stack (api/server.py),
    so an unexempted preflight is rejected here before CORSMiddleware ever
    gets to answer it -- the browser then blocks the real request even with
    a valid key. This is not a route handler reachable from outside; CORS
    preflight is answered entirely by CORSMiddleware, never by application
    code, so exempting it here does not weaken auth on any real request."""
    async def unreachable(request: Request) -> PlainTextResponse:
        return PlainTextResponse("should not be called by this test")

    set_identity_service(IdentityService(api_keys={}))
    mw = AuthMiddleware(None)
    scope = {
        "type": "http", "method": "OPTIONS", "path": "/api/goals/",
        "headers": [
            (b"origin", b"http://localhost:5173"),
            (b"access-control-request-method", b"GET"),
        ],
        "client": ("1.2.3.4", 1234),
    }
    response = asyncio.run(mw.dispatch(Request(scope), unreachable))
    assert response.status_code == 200


def _full_app_client(api_keys: dict[str, str]):
    """Build a real TestClient against the actual FastAPI app -- not just
    AuthMiddleware in isolation -- because the preflight bug this file
    guards against was specifically a middleware-*interaction* bug that
    isolated dispatch() tests could not catch.

    Note: config.settings is built once at import time (see conftest.py's
    own warning), so JARVIS_API_KEYS set here would arrive too late to take
    effect. Inject the IdentityService directly instead -- the same pattern
    every other test in this file already uses.
    """
    set_identity_service(IdentityService(api_keys=api_keys))
    from starlette.testclient import TestClient
    from api.server import app
    return TestClient(app)


def test_full_app_cross_origin_authenticated_flow():
    """End-to-end: a browser-like cross-origin client (the dashboard's own
    :5173 -> :8000 topology) must be able to preflight, then complete a real
    authenticated request and get a CORS-headered response back."""
    client = _full_app_client({"dashboard-token": "owner"})
    origin = "http://localhost:5173"

    preflight = client.options(
        "/api/goals/",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers.get("access-control-allow-origin") == origin

    unauthenticated = client.get("/api/goals/", headers={"Origin": origin})
    assert unauthenticated.status_code == 401

    authenticated = client.get(
        "/api/goals/",
        headers={"Origin": origin, "Authorization": "Bearer dashboard-token"},
    )
    assert authenticated.status_code == 200
    assert authenticated.headers.get("access-control-allow-origin") == origin
