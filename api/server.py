"""FastAPI server — public HTTP surface."""
from __future__ import annotations

import logging

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuthMiddleware)

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
