"""AuthMiddleware — resolves a Principal for every request (non-enforcing).

Foundation behavior: a ``Bearer`` token that matches a configured API key
resolves to that key's principal; anything else (including no header at all)
falls back to the owner principal, so single-user operation is unchanged.
Enforcement (rejecting unknown credentials) is a future phase — flipping it
on is a policy change here, not an architecture change.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from identity import get_identity_service


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        identity = get_identity_service()
        principal = identity.default_principal()
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            resolved = identity.resolve(auth[7:])
            if resolved is not None:
                principal = resolved
        request.state.principal = principal
        return await call_next(request)
