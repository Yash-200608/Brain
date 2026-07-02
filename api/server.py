"""FastAPI server — public HTTP surface."""
from __future__ import annotations

import logging

import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings

from api.middleware.auth import AuthMiddleware
from api.middleware.rate_limit import RateLimitMiddleware
from api.routes import goals as goals_route
from api.routes import memory as memory_route
from api.routes import query as query_route
from api.routes import sessions as sessions_route
from logs.logger import configure_logging

configure_logging()
logger = logging.getLogger("api")

app = FastAPI(title="Jarvis Brain", version="2.0.0-foundation")

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Without this, an unhandled exception (e.g. a downstream ModelProviderError
    when Ollama is unreachable) propagates past CORSMiddleware's normal response
    path -- a cross-origin caller (the dashboard) then sees an opaque network
    failure ("Failed to fetch") indistinguishable from a CORS or auth problem,
    instead of a readable error. This does not change what's wrong, only makes
    the failure legible to the caller that hit it.

    CORSMiddleware does not reliably attach headers to responses that
    originate from this handler -- both RateLimitMiddleware and AuthMiddleware
    are BaseHTTPMiddleware subclasses positioned between CORSMiddleware and
    the app, and Starlette's BaseHTTPMiddleware has a known gap in how
    exception-originated responses propagate back through that chain (found
    by direct verification, not assumed). Attach the header explicitly here
    rather than relying on it -- checked against the same allowlist
    CORSMiddleware itself uses, not echoed unconditionally.
    """
    logger.exception("unhandled exception on %s %s", request.method, request.url.path)
    response = JSONResponse(
        {"error": "internal_error", "detail": str(exc)},
        status_code=500,
    )
    origin = request.headers.get("origin")
    if origin in settings.cors_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
    return response

# Routers
app.include_router(query_route.router, prefix="/api", tags=["query"])
app.include_router(memory_route.router, prefix="/api/memory", tags=["memory"])
app.include_router(goals_route.router, prefix="/api/goals", tags=["goals"])
app.include_router(sessions_route.router, prefix="/api/sessions", tags=["sessions"])


@app.get("/health")
def health() -> dict:
    components = {"api": "ok", "orchestrator": "ok"}
    try:
        r = requests.get(f"{settings.ollama_base_url}/api/tags", timeout=2)
        components["ollama"] = "ok" if r.ok else "degraded"
    except requests.RequestException:
        components["ollama"] = "down"
    status = "ok" if all(v == "ok" for v in components.values()) else "degraded"
    return {"status": status, "components": components}
