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
            bucket = [t for t in self._buckets[client] if t > now - self.per]
            self._buckets[client] = bucket
            if len(bucket) >= self.rate:
                return JSONResponse({"error": "rate limit exceeded"}, status_code=429)
            bucket.append(now)
            self._prune(now)
        return await call_next(request)

    def _prune(self, now: float) -> None:
        """Drop buckets whose newest entry has aged out, so the per-IP dict
        cannot grow without bound across many distinct clients."""
        if len(self._buckets) <= 1024:
            return
        cutoff = now - self.per
        stale = [k for k, v in self._buckets.items() if not v or v[-1] <= cutoff]
        for k in stale:
            del self._buckets[k]
