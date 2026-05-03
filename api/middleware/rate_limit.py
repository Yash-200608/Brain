"""RateLimitMiddleware — token-bucket per client IP."""
from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, rate: int = 60, per_seconds: int = 60) -> None:
        super().__init__(app)
        self.rate = rate
        self.per = per_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    async def dispatch(self, request: Request, call_next):
        client = request.client.host if request.client else "anon"
        now = time.time()
        with self._lock:
            bucket = self._buckets[client]
            self._buckets[client] = [t for t in bucket if t > now - self.per]
            if len(self._buckets[client]) >= self.rate:
                return JSONResponse({"error": "rate limit exceeded"}, status_code=429)
            self._buckets[client].append(now)
        return await call_next(request)
