"""BrainMqttClient unit tests -- no live broker required.

Mirrors jarvis_node_sdk/tests/test_transport.py's exact technique: fake
publish() directly, drive with asyncio.run() in plain sync test functions
(this repo has no pytest-asyncio dependency and shouldn't gain one for a
milestone this small).
"""

from __future__ import annotations

import asyncio

from mqtt.client import BrainMqttClient, _topic_matches


def _make_faked_client() -> tuple[BrainMqttClient, dict]:
    client = BrainMqttClient(host="localhost", port=1883, client_id="test")
    captured: dict = {}

    async def fake_publish(topic, payload, *, qos=None, retain=False):
        captured["topic"] = topic
        captured["payload"] = payload
        pending = client._pending[payload["request_id"]]
        if not pending.future.done():
            pending.future.set_result(payload)

    client.publish = fake_publish  # type: ignore[method-assign]
    return client, captured


def test_request_generates_id_when_absent() -> None:
    client, captured = _make_faked_client()
    result = asyncio.run(
        client.request(
            topic="chimera/testnode/cmd",
            payload={"action": "ping"},
            reply_topic="chimera/testnode/response",
            timeout=1.0,
        )
    )
    assert "request_id" in captured["payload"]
    assert captured["payload"]["request_id"] == result["request_id"]


def test_request_preserves_caller_supplied_request_id() -> None:
    client, captured = _make_faked_client()
    result = asyncio.run(
        client.request(
            topic="chimera/testnode/cmd",
            payload={"action": "ping", "request_id": "caller-id"},
            reply_topic="chimera/testnode/response",
            timeout=1.0,
        )
    )
    assert captured["payload"]["request_id"] == "caller-id"
    assert result["request_id"] == "caller-id"


def test_subscribe_registers_handler_without_a_connection() -> None:
    client, _ = _make_faked_client()

    async def _noop(topic, payload):
        return None

    asyncio.run(client.subscribe("chimera/testnode/event", _noop))
    assert "chimera/testnode/event" in client._handlers


def test_dispatch_loop_routes_payload_to_handler() -> None:
    """No 1:1 transport.py precedent -- publish()-faking alone doesn't
    exercise the receive path, so this drives _dispatch_loop directly
    against a fake async-iterable of fake MQTT messages."""
    client, _ = _make_faked_client()
    seen = []

    async def _handler(topic, payload):
        seen.append((topic, payload))

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
        """_dispatch_loop reads `client.messages`, not `client` itself."""

        def __init__(self, messages):
            self.messages = messages

    async def run():
        await client.subscribe("chimera/testnode/state", _handler)
        fake_client = _FakeAiomqttClient(
            _FakeMessages([_FakeMsg("chimera/testnode/state", b'{"x": 1}')])
        )
        await client._dispatch_loop(fake_client)

    asyncio.run(run())
    assert seen == [("chimera/testnode/state", {"x": 1})]


def test_stop_cancels_pending_request_futures() -> None:
    """stop() must not leave a caller awaiting request() hanging forever."""
    client = BrainMqttClient(host="localhost", port=1883, client_id="test")

    async def fake_publish(topic, payload, *, qos=None, retain=False):
        # Deliberately never resolve the pending future -- simulates a
        # request that's still in flight when shutdown happens.
        return None

    client.publish = fake_publish  # type: ignore[method-assign]

    async def run():
        request_task = asyncio.create_task(
            client.request(
                topic="chimera/testnode/cmd",
                payload={"action": "ping"},
                reply_topic="chimera/testnode/response",
                timeout=30.0,
            )
        )
        await asyncio.sleep(0)  # let request() register its pending future
        await client.stop()
        try:
            await request_task
        except asyncio.CancelledError:
            return "cancelled"

    result = asyncio.run(run())
    assert result == "cancelled"


# ---------------------------------------------------------------------- #
# Single-level ("+") wildcard topic dispatch (Priority #3 Milestone 5) -- #
# added for the first real caller that needs it, a presence subscriber.  #
# ---------------------------------------------------------------------- #


def test_topic_matches_single_level_wildcard() -> None:
    assert _topic_matches("chimera/+/presence", "chimera/pc-main/presence") is True
    assert _topic_matches("chimera/+/presence", "chimera/phone-1/presence") is True


def test_topic_matches_rejects_segment_count_mismatch() -> None:
    assert _topic_matches("chimera/+/presence", "chimera/pc-main/presence/extra") is False
    assert _topic_matches("chimera/+/presence", "chimera/presence") is False


def test_topic_matches_rejects_wrong_fixed_segment() -> None:
    assert _topic_matches("chimera/+/presence", "chimera/pc-main/state") is False


def test_topic_matches_exact_pattern_behaves_as_equality() -> None:
    assert _topic_matches("chimera/testnode/state", "chimera/testnode/state") is True
    assert _topic_matches("chimera/testnode/state", "chimera/other/state") is False


def test_topic_matches_rejects_empty_segment() -> None:
    """+ must match a non-empty segment -- a malformed topic like
    "chimera//presence" must not satisfy "chimera/+/presence"."""
    assert _topic_matches("chimera/+/presence", "chimera//presence") is False


def test_dispatch_loop_routes_wildcard_subscription() -> None:
    client, _ = _make_faked_client()
    seen = []

    async def _handler(topic, payload):
        seen.append((topic, payload))

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

    async def run():
        await client.subscribe("chimera/+/presence", _handler)
        fake_client = _FakeAiomqttClient(
            _FakeMessages([_FakeMsg("chimera/pc-main/presence", b'{"x": 1}')])
        )
        await client._dispatch_loop(fake_client)

    asyncio.run(run())
    assert seen == [("chimera/pc-main/presence", {"x": 1})]


def test_dispatch_loop_exact_match_unaffected_by_wildcard_scan() -> None:
    """A concrete-topic subscriber and an unrelated wildcard subscriber
    both registered -- only the exact-match handler should fire for a
    message that doesn't satisfy the wildcard pattern."""
    client, _ = _make_faked_client()
    exact_seen = []
    wildcard_seen = []

    async def _exact_handler(topic, payload):
        exact_seen.append((topic, payload))

    async def _wildcard_handler(topic, payload):
        wildcard_seen.append((topic, payload))

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

    async def run():
        await client.subscribe("chimera/testnode/state", _exact_handler)
        await client.subscribe("chimera/+/other", _wildcard_handler)
        fake_client = _FakeAiomqttClient(
            _FakeMessages([_FakeMsg("chimera/testnode/state", b'{"x": 1}')])
        )
        await client._dispatch_loop(fake_client)

    asyncio.run(run())
    assert exact_seen == [("chimera/testnode/state", {"x": 1})]
    assert wildcard_seen == []
