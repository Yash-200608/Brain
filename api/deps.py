"""Shared FastAPI dependencies for the HTTP API.

`require_scope` is the authorization layer that sits on top of
AuthMiddleware's authentication (Priority #4 Milestone 1). AuthMiddleware
has already resolved and attached `request.state.principal` for every
non-exempt path, or rejected the request with 401 before any route runs;
this dependency then checks that the resolved principal actually holds the
scope a given route requires. A valid-but-under-privileged principal gets
403 (known, not permitted), never 401.

Wired per-route rather than globally so every route visibly declares its
own required scope at the point of definition -- the scope enforcement is
auditable by reading the route, not by cross-referencing a central table.
"""
from __future__ import annotations

from fastapi import HTTPException, Request

from identity import Principal


def require_scope(scope: str):
    """Build a dependency that requires the request's principal to hold `scope`.

    Returns the `Principal` on success so a handler may also depend on it
    directly (``principal: Principal = Depends(require_scope(...))``) when it
    needs the identity, though most routes attach it via ``dependencies=[...]``
    purely for the side-effecting check.
    """

    def _dep(request: Request) -> Principal:
        principal = getattr(request.state, "principal", None)
        if principal is None:
            # Defensive: AuthMiddleware guarantees a principal on any
            # non-exempt path. Never trust that invariant for an authz
            # decision -- absence resolves to rejection, not permission
            # (fail-closed, NP-3 / Ecosystem Architecture Section 6.1).
            raise HTTPException(status_code=401, detail="unauthenticated")
        if not principal.has_scope(scope):
            raise HTTPException(
                status_code=403, detail=f"missing required scope: {scope}"
            )
        return principal

    return _dep
