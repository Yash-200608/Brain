"""Route-level scope enforcement (Priority #4 Milestone 1).

Proves every protected route now authorizes on top of authentication: a
validly-authenticated principal that lacks the route's required scope gets
403 (not 401 -- it is known, just not permitted), and a principal holding
the scope passes the check. `admin` implies every scope.

Technique mirrors test_auth_middleware.py / test_devices_route.py: inject an
IdentityService directly (config.settings is built once at import time, too
early for JARVIS_API_KEYS to matter) and register keys whose principals
carry exactly the scopes under test.
"""
from __future__ import annotations

from starlette.testclient import TestClient

from api.middleware.rate_limit import RateLimitMiddleware
from api.server import app
from identity import (
    SCOPE_ADMIN,
    SCOPE_DEVICES_ACTION,
    SCOPE_DEVICES_APPROVE,
    SCOPE_DEVICES_READ,
    SCOPE_GOALS,
    SCOPE_MEMORY_READ,
    SCOPE_MEMORY_WRITE,
    SCOPE_QUERY,
    SCOPE_SESSIONS,
    IdentityService,
    Principal,
    set_identity_service,
)


def teardown_function() -> None:
    set_identity_service(None)
    # Scope tests fire many authenticated requests through one TestClient IP;
    # clear the shared app's rate-limit buckets so later tests in this module
    # (and the full suite) do not inherit a 429 from the route sweep above.
    stack = app.middleware_stack
    while stack is not None:
        if isinstance(stack, RateLimitMiddleware):
            with stack._lock:
                stack._buckets.clear()
        stack = getattr(stack, "app", None)


def _client_with_scopes(*scopes: str) -> TestClient:
    """A TestClient whose only key 'tok' resolves to a principal holding
    exactly `scopes` (no more)."""
    svc = IdentityService(api_keys={})
    svc.register_key(
        "tok", Principal(user_id="u", client_id="api", scopes=frozenset(scopes))
    )
    set_identity_service(svc)
    return TestClient(app)


_AUTH = {"Authorization": "Bearer tok"}

# (method, path, required_scope) for every protected route in the app.
_ROUTES = [
    ("post", "/api/query", SCOPE_QUERY),
    ("post", "/api/memory/search", SCOPE_MEMORY_READ),
    ("post", "/api/memory/write", SCOPE_MEMORY_WRITE),
    ("get", "/api/goals/", SCOPE_GOALS),
    ("post", "/api/goals/", SCOPE_GOALS),
    ("get", "/api/goals/some-id", SCOPE_GOALS),
    ("get", "/api/sessions/", SCOPE_SESSIONS),
    ("get", "/api/sessions/some-id/turns", SCOPE_SESSIONS),
    ("get", "/api/devices/", SCOPE_DEVICES_READ),
    ("get", "/api/devices/approvals", SCOPE_DEVICES_READ),
    ("get", "/api/devices/audit", SCOPE_DEVICES_READ),
    ("get", "/api/devices/trial-report", SCOPE_DEVICES_READ),
    ("get", "/api/devices/some-node", SCOPE_DEVICES_READ),
    ("post", "/api/devices/some-node/ping", SCOPE_DEVICES_ACTION),
    ("post", "/api/devices/some-node/invoke", SCOPE_DEVICES_ACTION),
    ("post", "/api/devices/approvals/some-approval/approve", SCOPE_DEVICES_APPROVE),
    ("post", "/api/devices/approvals/some-approval/deny", SCOPE_DEVICES_APPROVE),
]

# A scope that no route requires -- holding only this must be rejected
# everywhere, proving no route is silently unprotected.
_INERT_SCOPE = "unrelated.scope"


def _call(client: TestClient, method: str, path: str):
    fn = getattr(client, method)
    return fn(path, headers=_AUTH, json={}) if method == "post" else fn(path, headers=_AUTH)


def test_every_route_403s_when_scope_missing() -> None:
    """The core M1 property: a principal with an unrelated scope is forbidden
    on every protected route -- there is no route without a scope gate."""
    for method, path, _required in _ROUTES:
        client = _client_with_scopes(_INERT_SCOPE)
        r = _call(client, method, path)
        assert r.status_code == 403, f"{method.upper()} {path} should be 403 without its scope, got {r.status_code}"
        teardown_function()


def test_each_route_passes_its_own_scope() -> None:
    """Holding exactly the required scope clears the authorization gate --
    the response is anything but 401/403 (the downstream handler may 200,
    404, 503, etc., but the scope check itself passed)."""
    for method, path, required in _ROUTES:
        client = _client_with_scopes(required)
        r = _call(client, method, path)
        assert r.status_code not in (401, 403), (
            f"{method.upper()} {path} should clear authz with {required}, got {r.status_code}"
        )
        teardown_function()


def test_admin_scope_implies_every_route() -> None:
    """`admin` implies all scopes (Principal.has_scope) -- an admin-only
    principal clears every gate."""
    for method, path, _required in _ROUTES:
        client = _client_with_scopes(SCOPE_ADMIN)
        r = _call(client, method, path)
        assert r.status_code not in (401, 403), (
            f"{method.upper()} {path} should clear authz for admin, got {r.status_code}"
        )
        teardown_function()


def test_devices_read_cannot_invoke_action() -> None:
    """The read/action split: a key that may read the registry must NOT be
    able to command a device (ping). This is the NP-7 privilege boundary the
    later dispatch/approval endpoints rely on."""
    client = _client_with_scopes(SCOPE_DEVICES_READ)

    assert client.get("/api/devices/", headers=_AUTH).status_code == 200
    # ping requires devices.action -- forbidden with only devices.read, and
    # the 403 fires before the mqtt-disabled 503 (dependency precedes handler)
    r = client.post("/api/devices/some-node/ping", headers=_AUTH)
    assert r.status_code == 403


def test_unauthenticated_still_401_not_403() -> None:
    """Authorization does not shadow authentication: no token is still 401,
    not 403 (rejection at the auth layer, before any scope check)."""
    client = _client_with_scopes(SCOPE_GOALS)
    r = client.get("/api/goals/")  # no Authorization header
    assert r.status_code == 401
