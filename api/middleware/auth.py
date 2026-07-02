"""AuthMiddleware — resolves a Principal for every request, fail-closed.

A ``Bearer`` token that matches a configured API key resolves to that key's
principal. Anything else -- no header, a malformed header, or a token that
does not resolve -- is rejected with 401. There is no fallback to the owner
principal for network requests: an unauthenticated caller is not the owner,
it is unauthenticated (Ecosystem Architecture Section 6.1 -- verification
failure is rejection, not a distinct trust tier).

This governs the HTTP API surface only. In-process callers (the CLI, calling
the orchestrator directly) never pass through this middleware and are
unaffected. ``/health`` is exempt -- it leaks no sensitive state.

Operational note: ``settings.api_keys`` is empty by default, so until at
least one key is configured (``JARVIS_API_KEYS`` env var) and presented by
callers (e.g. the dashboard), every HTTP API request will be rejected. That
is the correct behavior for a service with no provisioned credentials, not a
regression -- silently treating "no credential" as "the owner" is exactly
the bug this closes.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from identity import get_identity_service

_EXEMPT_PATHS = frozenset({"/health"})


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        identity = get_identity_service()
        auth = request.headers.get("authorization", "")
        principal = None
        if auth.lower().startswith("bearer "):
            principal = identity.resolve(auth[7:])

        if principal is None:
            return JSONResponse(
                {"error": "unauthorized", "detail": "missing or invalid bearer token"},
                status_code=401,
            )

        request.state.principal = principal
        return await call_next(request)
