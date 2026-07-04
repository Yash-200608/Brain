"""Proves send_command_and_await_response()'s Priority #4 Milestone 2
additions: request_id correlation (safe for concurrent overlapping
commands to the same node+action) and shared-subscription reuse (no more
handler-per-call accumulation). test_mqtt_signed_command.py's existing
tests already cover the pre-M2 (verb, action) fallback path unchanged
(its fake responses never set request_id) -- this file covers only the
new properties.

Same fake-broker technique as test_mqtt_signed_command.py: a
BrainMqttClient whose publish() -- when publishing to a /cmd topic --
synthesizes a response and feeds it through the real _dispatch_loop().
"""

from __future__ import annotations

import asyncio
import json

from mqtt.client import BrainMqttClient
from mqtt.signed import send_command_and_await_response
from protocols.chimera_contract import ChimeraEnvelope, sign

KEY = "f" * 64
NODE = "jarvis-core-pc"


class _FakeMsg:
    def __init__(self, topic, payload):
        self.topic = topic
        self.payload = payload


class _FakeMessages:
    def __init__(self, msgs):
        self._msgs = msgs

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for m in self._msgs:
            yield m


class _FakeAiomqttClient:
    def __init__(self, messages):
        self.messages = messages


def _make_client_with_simulated_responder(response_builder):
    client = BrainMqttClient(host="localhost", port=1883, client_id="test")

    async def fake_publish(topic, payload, *, qos=None, retain=False):
        if not topic.endswith("/cmd"):
            return
        response_payload = response_builder(payload)
        if response_payload is None:
            return
        data = json.dumps(response_payload, separators=(",", ":")).encode()
        fake_aiomqtt = _FakeAiomqttClient(
            _FakeMessages([_FakeMsg(f"chimera/{NODE}/response", data)])
        )
        await client._dispatch_loop(fake_aiomqtt)

    client.publish = fake_publish  # type: ignore[method-assign]
    return client


def _valid_response(action: str, params: dict):
    def build(cmd_payload):
        response = ChimeraEnvelope(node=NODE, verb="response", action=action, params=params)
        return sign(response, KEY).model_dump()

    return build


def test_concurrent_commands_correlate_by_request_id_even_answered_out_of_order() -> None:
    """Two commands to the same node+action in flight at once, answered in
    the REVERSE order they were sent -- each caller must get its own
    result, matched by request_id, not by send order or a shared future."""
    client = BrainMqttClient(host="localhost", port=1883, client_id="test")
    published_cmds: list[dict] = []

    async def fake_publish(topic, payload, *, qos=None, retain=False):
        if topic.endswith("/cmd"):
            published_cmds.append(payload)

    client.publish = fake_publish  # type: ignore[method-assign]

    def _signed_response(request_id: str, which: str) -> dict:
        response = ChimeraEnvelope(
            node=NODE,
            verb="response",
            action="ping",
            params={"which": which},
            request_id=request_id,
        )
        return sign(response, KEY).model_dump()

    async def run():
        task_a = asyncio.create_task(
            send_command_and_await_response(client, NODE, "ping", {"call": "A"}, KEY, timeout=2.0)
        )
        task_b = asyncio.create_task(
            send_command_and_await_response(client, NODE, "ping", {"call": "B"}, KEY, timeout=2.0)
        )
        while len(published_cmds) < 2:
            await asyncio.sleep(0)

        request_id_a = published_cmds[0]["request_id"]
        request_id_b = published_cmds[1]["request_id"]
        assert request_id_a and request_id_b and request_id_a != request_id_b

        # Feed B's response first, then A's -- correlation must not depend
        # on send order or arrival order.
        fake_aiomqtt = _FakeAiomqttClient(
            _FakeMessages(
                [
                    _FakeMsg(
                        f"chimera/{NODE}/response",
                        json.dumps(
                            _signed_response(request_id_b, "B"), separators=(",", ":")
                        ).encode(),
                    ),
                    _FakeMsg(
                        f"chimera/{NODE}/response",
                        json.dumps(
                            _signed_response(request_id_a, "A"), separators=(",", ":")
                        ).encode(),
                    ),
                ]
            )
        )
        await client._dispatch_loop(fake_aiomqtt)

        return await asyncio.gather(task_a, task_b)

    result_a, result_b = asyncio.run(run())

    assert result_a is not None and result_a.params == {"which": "A"}
    assert result_b is not None and result_b.params == {"which": "B"}


def test_response_with_unmatched_request_id_does_not_fall_back() -> None:
    """A response carrying a request_id that matches nothing pending must
    NOT resolve via the (verb, action) fallback -- falling back on a
    request_id mismatch would defeat the safety correlation exists for."""

    def build(cmd_payload):
        response = ChimeraEnvelope(
            node=NODE,
            verb="response",
            action="ping",
            params={"pong": True},
            request_id="not-the-real-one",
        )
        return sign(response, KEY).model_dump()

    client = _make_client_with_simulated_responder(build)

    result = asyncio.run(
        send_command_and_await_response(client, NODE, "ping", {}, KEY, timeout=0.1)
    )

    assert result is None


def test_repeated_calls_share_one_subscription_not_accumulate() -> None:
    """The Priority #3 closure's accumulation gap: two sequential calls on
    the same client+node must register exactly one handler on the response
    topic, not two."""
    client = _make_client_with_simulated_responder(_valid_response("ping", {"pong": True}))

    asyncio.run(send_command_and_await_response(client, NODE, "ping", {}, KEY, timeout=1.0))
    asyncio.run(send_command_and_await_response(client, NODE, "ping", {}, KEY, timeout=1.0))

    topic = f"chimera/{NODE}/response"
    assert len(client._handlers.get(topic, [])) == 1
