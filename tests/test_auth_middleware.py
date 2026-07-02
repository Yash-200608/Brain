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
