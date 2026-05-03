"""AuthMiddleware — placeholder, allow-by-default for now (V5 hardens)."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # TODO V5: validate API key / JWT against settings.api_keys
        return await call_next(request)
