"""FastAPI server — public HTTP surface."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings

from api.middleware.auth import AuthMiddleware
from api.middleware.rate_limit import RateLimitMiddleware
from api.routes import devices as devices_route
from api.routes import goals as goals_route
from api.routes import memory as memory_route
from api.routes import query as query_route
from api.routes import sessions as sessions_route
from logs.logger import configure_logging
from mqtt import get_mqtt_client

configure_logging()
logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Starts Brain's MQTT client only when settings.mqtt_enabled is true.

    Default (mqtt_enabled=False): a true no-op -- no task spawned, no
    connection attempted. Priority #3 Milestone 2 gives Brain the
    capability to speak MQTT; Milestone 5 adds its first real consumer
    (chimera/+/presence) and Milestone 7 adds a second (chimera/+/state) --
    when enabled AND settings.mqtt_hmac_key is set, both subscribe and
    record inbound data into the same DeviceStore. If mqtt_enabled is true
    but no HMAC key is configured, the client still starts (other future
    subscribers may not need signing) but both subscriptions are skipped
    with a warning, rather than subscribing handlers that can structurally
    never verify anything.
    """
    mqtt_client = None
    if settings.mqtt_enabled:
        logger.info("mqtt enabled -- starting background client")
        mqtt_client = get_mqtt_client()
        await mqtt_client.start()

        if settings.mqtt_hmac_key:
            from devices.store import DeviceStore
            from mqtt.presence import make_presence_handler
            from mqtt.state import make_state_handler

            device_store = DeviceStore()
            await mqtt_client.subscribe(
                "chimera/+/presence",
                make_presence_handler(device_store, settings.mqtt_hmac_key),
            )
            await mqtt_client.subscribe(
                "chimera/+/state",
                make_state_handler(device_store, settings.mqtt_hmac_key),
            )
        else:
            logger.warning(
                "mqtt_hmac_key not set -- skipping chimera/+/presence and "
                "chimera/+/state subscriptions"
            )
    else:
        logger.debug("mqtt disabled -- lifespan is a no-op")
    yield
    if mqtt_client is not None:
        await mqtt_client.stop()


app = FastAPI(title="Jarvis Brain", version="2.0.0-foundation", lifespan=lifespan)

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
app.include_router(devices_route.router, prefix="/api/devices", tags=["devices"])


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
