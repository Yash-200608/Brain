"""BrainMqttClient -- minimal async MQTT connectivity primitive for Brain.

Priority #3 Milestone 2 scope: prove Brain can connect, publish, subscribe,
and correlate request/response over MQTT. Deliberately envelope-agnostic --
does not know about ChimeraEnvelope, does not sign/verify, does not wire into
EventBus. Mirrors the connect/reconnect-supervisor design of JARVIS's
jarvis_node_sdk/transport.py (MqttTransport), trimmed to what Brain actually
needs right now:

Kept: publish/subscribe/request (+ request_id correlation), and the
never-raising supervised reconnect loop -- the never-raise behavior is what
makes it safe to start as a background task from api/server.py's lifespan
without risking app startup.

Trimmed, not ported (no current callers, easy to add when one exists):
iter_messages() queue helper, LWT/will payload (a liveness feature nobody's
watching yet -- Device Registry territory), TLS context.

Priority #3 Milestone 5 adds single-level ("+") wildcard topic dispatch --
the first caller that needs it (a chimera/+/presence subscriber) now
exists. Multi-level ("#") wildcard dispatch remains deferred; nothing
needs fan-out across verbs yet.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

import aiomqtt

from config import settings

logger = logging.getLogger("mqtt")

JsonDict = dict[str, Any]
Handler = Callable[[str, JsonDict], Awaitable[None]]


def _topic_matches(pattern: str, topic: str) -> bool:
    """True if concrete `topic` satisfies subscription `pattern`.

    Supports MQTT single-level wildcard ("+") in any segment position.
    Does NOT support multi-level wildcard ("#") -- no caller needs it yet.
    Segment count must match exactly; "+" matches exactly one non-empty
    segment, never zero segments or an empty segment (a malformed topic
    like "chimera//presence" must not satisfy "chimera/+/presence").
    """
    pattern_parts = pattern.split("/")
    topic_parts = topic.split("/")
    if len(pattern_parts) != len(topic_parts):
        return False
    return all(
        (p == "+" and t != "") or p == t
        for p, t in zip(pattern_parts, topic_parts)
    )


@dataclass
class _PendingRequest:
    future: "asyncio.Future[JsonDict]"
    sent_at: float = field(default_factory=time.monotonic)


class BrainMqttClient:
    """Async MQTT client with a supervised auto-reconnect loop.

    Envelope-agnostic: publish()/subscribe() move plain JSON-able dicts.
    Callers are responsible for any signing (protocols.chimera_contract's
    sign()/verify()) before publish() and after subscribe() delivers a
    payload -- reconciling that is explicitly out of scope for this
    milestone.
    """

    def __init__(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
        client_id: str | None = None,
        keepalive: int | None = None,
        qos: int | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self._host = host or settings.mqtt_host
        self._port = port if port is not None else settings.mqtt_port
        self._client_id = client_id or settings.mqtt_client_id
        self._keepalive = keepalive if keepalive is not None else settings.mqtt_keepalive
        self._qos = qos if qos is not None else settings.mqtt_qos
        self._username = username if username is not None else settings.mqtt_username
        self._password = password if password is not None else settings.mqtt_password

        self._client: aiomqtt.Client | None = None
        self._supervisor: asyncio.Task[None] | None = None
        self._connected = asyncio.Event()
        self._stopping = asyncio.Event()

        self._handlers: dict[str, list[Handler]] = {}
        self._pending: dict[str, _PendingRequest] = {}

    # ------------------------------------------------------------------ #
    # Lifecycle                                                          #
    # ------------------------------------------------------------------ #

    async def start(self) -> None:
        """Spawn the supervisor task and wait for the first connection."""
        self._stopping.clear()
        self._supervisor = asyncio.create_task(self._supervise(), name="brain-mqtt-supervisor")
        await self._connected.wait()

    async def stop(self) -> None:
        """Cancel the supervisor and unblock any pending request() futures."""
        self._stopping.set()
        if self._supervisor:
            self._supervisor.cancel()
            try:
                await self._supervisor
            except (asyncio.CancelledError, Exception):
                pass
        for pending in self._pending.values():
            if not pending.future.done():
                pending.future.cancel()
        self._pending.clear()

    async def __aenter__(self) -> "BrainMqttClient":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()

    # ------------------------------------------------------------------ #
    # Supervised connect loop                                            #
    # ------------------------------------------------------------------ #

    async def _supervise(self) -> None:
        backoff = 1.0
        max_backoff = 60.0
        while not self._stopping.is_set():
            try:
                logger.info(
                    "mqtt connecting to %s:%s as %r", self._host, self._port, self._client_id
                )
                async with aiomqtt.Client(
                    hostname=self._host,
                    port=self._port,
                    identifier=self._client_id,
                    username=self._username,
                    password=self._password,
                    keepalive=self._keepalive,
                ) as client:
                    self._client = client
                    self._connected.set()
                    backoff = 1.0
                    for topic in list(self._handlers.keys()):
                        await client.subscribe(topic, qos=self._qos)
                    await self._dispatch_loop(client)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 -- never let the supervisor die
                logger.warning("mqtt disconnected: %r -- retry in %.1fs", exc, backoff)
            finally:
                self._client = None
                self._connected.clear()

            if self._stopping.is_set():
                break
            try:
                await asyncio.wait_for(self._stopping.wait(), timeout=backoff)
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, max_backoff)

    async def _dispatch_loop(self, client: aiomqtt.Client) -> None:
        async for msg in client.messages:
            topic = str(msg.topic)
            try:
                payload: JsonDict = json.loads(msg.payload.decode())
            except (UnicodeDecodeError, json.JSONDecodeError):
                logger.warning("non-JSON payload on %r -- dropping", topic)
                continue

            rid = payload.get("request_id")
            if rid and rid in self._pending:
                pending = self._pending.pop(rid)
                if not pending.future.done():
                    pending.future.set_result(payload)

            handlers = list(self._handlers.get(topic, []))
            for pattern, pattern_handlers in self._handlers.items():
                if pattern != topic and "+" in pattern and _topic_matches(pattern, topic):
                    handlers.extend(pattern_handlers)

            for handler in handlers:
                try:
                    await handler(topic, payload)
                except Exception:  # noqa: BLE001
                    logger.exception("handler for %r raised", topic)

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #

    async def wait_connected(self, timeout: float | None = None) -> None:
        await asyncio.wait_for(self._connected.wait(), timeout=timeout)

    async def subscribe(self, topic: str, handler: Handler) -> None:
        self._handlers.setdefault(topic, []).append(handler)
        if self._client is not None:
            await self._client.subscribe(topic, qos=self._qos)

    async def publish(
        self, topic: str, payload: JsonDict, *, qos: int | None = None, retain: bool = False
    ) -> None:
        if self._client is None:
            await self.wait_connected(timeout=10.0)
        assert self._client is not None
        data = json.dumps(payload, separators=(",", ":")).encode()
        await self._client.publish(
            topic, data, qos=qos if qos is not None else self._qos, retain=retain
        )

    async def request(
        self, topic: str, payload: JsonDict, reply_topic: str, *, timeout: float = 30.0
    ) -> JsonDict:
        request_id = payload.get("request_id") or str(uuid.uuid4())
        payload = {**payload, "request_id": request_id}

        loop = asyncio.get_running_loop()
        future: "asyncio.Future[JsonDict]" = loop.create_future()
        self._pending[request_id] = _PendingRequest(future=future)

        if reply_topic not in self._handlers:
            await self.subscribe(reply_topic, self._noop_handler)

        try:
            await self.publish(topic, payload)
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("mqtt rpc timeout on %r rid=%s", topic, request_id)
            raise
        finally:
            self._pending.pop(request_id, None)

    @staticmethod
    async def _noop_handler(_topic: str, _payload: JsonDict) -> None:
        return None


# ---------------------------------------------------------------------- #
# Module-level singleton -- matches identity/service.py's exact shape.   #
# ---------------------------------------------------------------------- #

_client: BrainMqttClient | None = None
_client_lock = threading.Lock()


def get_mqtt_client() -> BrainMqttClient:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = BrainMqttClient()
    return _client


def set_mqtt_client(client: BrainMqttClient | None) -> None:
    """Replace the default client (primarily for tests)."""
    global _client
    with _client_lock:
        _client = client
