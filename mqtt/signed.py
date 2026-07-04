"""Signed-envelope/MQTT composition layer (Priority #3 Milestone 3).

Proves that protocols/chimera_contract.py's ChimeraEnvelope (Milestone 1)
and mqtt/client.py's BrainMqttClient (Milestone 2) compose correctly --
BrainMqttClient stays deliberately envelope-agnostic by its own docstring's
design commitment, so this thin module is where the two meet.

Does NOT do: topic construction (callers pass literal topic strings; no
real call site exists yet to design a builder against), EventBus wiring,
Device Registry, or anything involving a live broker.

Priority #3 Milestone 8 adds send_command_and_await_response() -- the
first bidirectional (publish-then-await) consumer, wiring the real
command path proven purely via hand-built dicts in Milestone 6.

Priority #4 Milestone 2 replaces that function's per-call subscribe() +
single-future wait with _ResponseCorrelator: one shared subscription per
(client, response-topic), matching inbound responses by the new
request_id field when present and falling back to (verb, action) when
not. This closes two items the Priority #3 closure flagged together --
"no request_id/correlation field" and "repeated calls ... accumulate
handlers" -- since both live at the same seam.
"""

from __future__ import annotations

import asyncio
import uuid
import weakref

from pydantic import ValidationError

from mqtt.client import BrainMqttClient, JsonDict
from protocols.chimera_contract import ChimeraEnvelope, sign, verify


async def publish_envelope(
    client: BrainMqttClient, topic: str, envelope: ChimeraEnvelope, key: str
) -> ChimeraEnvelope:
    """Signs `envelope` with `key`, publishes it, and returns the signed
    copy (callers/tests may want the nonce/sig that was actually sent).

    Signing happens here, not left to the caller -- prevents accidentally
    publishing an envelope with sig="" by forgetting to call sign() first.
    """
    signed = sign(envelope, key)
    await client.publish(topic, signed.model_dump())
    return signed


def verify_payload(payload: dict, key: str) -> ChimeraEnvelope | None:
    """Parses + verifies an inbound MQTT payload. Returns None on any
    failure (malformed shape, unknown/extra field, tampered field, expired
    timestamp, wrong key) rather than raising, so callers can write
    `if envelope := verify_payload(payload, key): ...`.
    """
    try:
        envelope = ChimeraEnvelope.model_validate(payload)
    except (ValidationError, TypeError):
        return None
    return envelope if verify(envelope, key) else None


class _ResponseCorrelator:
    """Tracks in-flight send_command_and_await_response() waiters for one
    (client, response-topic) pair, so repeated calls share a single
    subscription instead of each accumulating its own handler.

    Matching prefers request_id: a response that carries one is resolved
    *only* by exact request_id match (never falls through to the
    (verb, action) bucket) -- a stale or mismatched request_id must not
    spuriously resolve a different in-flight waiter, which would defeat
    the point of adding correlation. A response with no request_id at all
    (a responder that hasn't adopted the field) falls back to the oldest
    pending waiter for its action, preserving the pre-Milestone-2 behavior.

    One correlator is built per (client, topic) the first time
    send_command_and_await_response() is called for that pair, and is
    assumed to be used with a single, unchanging HMAC key for that pair's
    lifetime -- true in every real deployment (one Brain process holds
    exactly one settings.mqtt_hmac_key).
    """

    def __init__(self, key: str) -> None:
        self._key = key
        self._by_request_id: dict[str, asyncio.Future[ChimeraEnvelope]] = {}
        self._by_action: dict[str, list[asyncio.Future[ChimeraEnvelope]]] = {}

    def wait_for(self, request_id: str, action: str) -> "asyncio.Future[ChimeraEnvelope]":
        loop = asyncio.get_running_loop()
        future: asyncio.Future[ChimeraEnvelope] = loop.create_future()
        self._by_request_id[request_id] = future
        self._by_action.setdefault(action, []).append(future)
        return future

    def forget(
        self, request_id: str, action: str, future: "asyncio.Future[ChimeraEnvelope]"
    ) -> None:
        self._by_request_id.pop(request_id, None)
        bucket = self._by_action.get(action)
        if bucket and future in bucket:
            bucket.remove(future)
            if not bucket:
                del self._by_action[action]

    async def handle(self, topic: str, payload: JsonDict) -> None:
        envelope = verify_payload(payload, self._key)
        if envelope is None or envelope.verb != "response":
            return

        if envelope.request_id:
            future = self._by_request_id.pop(envelope.request_id, None)
            if future is not None and not future.done():
                future.set_result(envelope)
            return  # a request_id-bearing response only ever resolves by id

        bucket = self._by_action.get(envelope.action)
        if not bucket:
            return
        future = bucket.pop(0)
        if not bucket:
            del self._by_action[envelope.action]
        if not future.done():
            future.set_result(envelope)


_correlators: "weakref.WeakKeyDictionary[BrainMqttClient, dict[str, _ResponseCorrelator]]" = (
    weakref.WeakKeyDictionary()
)


async def _get_correlator(client: BrainMqttClient, topic: str, key: str) -> _ResponseCorrelator:
    """Returns the shared correlator for (client, topic), subscribing to
    `topic` exactly once no matter how many times this is called."""
    per_client = _correlators.setdefault(client, {})
    correlator = per_client.get(topic)
    if correlator is None:
        correlator = _ResponseCorrelator(key)
        per_client[topic] = correlator
        await client.subscribe(topic, correlator.handle)
    return correlator


async def send_command_and_await_response(
    client: BrainMqttClient,
    node: str,
    action: str,
    params: dict,
    key: str,
    *,
    timeout: float = 30.0,
) -> ChimeraEnvelope | None:
    """Signs+publishes a "cmd" envelope (carrying a fresh request_id) to
    chimera/{node}/cmd, then awaits the first inbound chimera/{node}/response
    message that verifies and correlates to this specific call. Returns
    None on timeout or verification failure -- never raises.

    Safe for concurrent overlapping commands to the same node+action: each
    call gets its own request_id, and _ResponseCorrelator matches on it
    rather than the bare (verb, action) equality Milestone 8 originally
    used. Repeated calls on the same client+node share one
    _ResponseCorrelator/subscription rather than accumulating a handler
    per call.
    """
    topic = f"chimera/{node}/response"
    correlator = await _get_correlator(client, topic, key)

    request_id = uuid.uuid4().hex
    future = correlator.wait_for(request_id, action)

    cmd = ChimeraEnvelope(node=node, verb="cmd", action=action, params=params, request_id=request_id)
    await publish_envelope(client, f"chimera/{node}/cmd", cmd, key)

    try:
        return await asyncio.wait_for(future, timeout=timeout)
    except asyncio.TimeoutError:
        return None
    finally:
        correlator.forget(request_id, action, future)
