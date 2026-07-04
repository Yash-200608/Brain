"""Proves send_command_and_await_response()'s REAL subscribe()+dispatch
wiring (Priority #3 Milestone 8) -- not just the pure sign/verify logic,
already covered by test_mqtt_cmd_dispatch.py's hand-built-dict tests.

Technique: fake client.publish() so that, when it publishes to a /cmd
topic, it synthesizes a response payload and feeds it through the REAL
client._dispatch_loop() (the same _FakeMsg/_FakeMessages/_FakeAiomqttClient
trio already used in test_mqtt_client.py) -- so the real
subscribe()-registered handler resolves the awaiting future, not a
shortcut.
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
    """A BrainMqttClient whose publish() -- when publishing to a /cmd
    topic -- synthesizes a response via response_builder(cmd_payload) and
    feeds it through the real _dispatch_loop(), proving the real
    subscribe()-registered handler resolves the awaiting future."""
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


def test_happy_path_resolves_with_verified_response() -> None:
    client = _make_client_with_simulated_responder(_valid_response("ping", {"pong": True}))

    result = asyncio.run(
        send_command_and_await_response(client, NODE, "ping", {}, KEY, timeout=1.0)
    )

    assert result is not None
    assert result.params == {"pong": True}


def test_mismatched_action_times_out() -> None:
    client = _make_client_with_simulated_responder(_valid_response("not-ping", {"pong": True}))

    result = asyncio.run(
        send_command_and_await_response(client, NODE, "ping", {}, KEY, timeout=0.1)
    )

    assert result is None


def test_tampered_response_times_out() -> None:
    def build(cmd_payload):
        response = ChimeraEnvelope(node=NODE, verb="response", action="ping", params={"pong": True})
        signed = sign(response, KEY).model_dump()
        return {**signed, "params": {"pong": False}}

    client = _make_client_with_simulated_responder(build)

    result = asyncio.run(
        send_command_and_await_response(client, NODE, "ping", {}, KEY, timeout=0.1)
    )

    assert result is None


def test_no_response_at_all_times_out() -> None:
    client = _make_client_with_simulated_responder(lambda cmd_payload: None)

    result = asyncio.run(
        send_command_and_await_response(client, NODE, "ping", {}, KEY, timeout=0.1)
    )

    assert result is None
