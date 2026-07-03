"""Proves protocols.chimera_contract's ChimeraEnvelope (Milestone 1) and
mqtt.client's BrainMqttClient (Milestone 2) compose correctly through
mqtt.signed's publish_envelope()/verify_payload() (Milestone 3).

No live broker required -- mirrors test_mqtt_client.py's fake-publish
technique, plain asyncio.run() in sync test functions.
"""

from __future__ import annotations

import asyncio
import json

from mqtt.client import BrainMqttClient
from mqtt.signed import publish_envelope, verify_payload
from protocols.chimera_contract import ChimeraEnvelope, RiskTier

KEY = "f" * 64


def _make_capturing_client() -> tuple[BrainMqttClient, dict]:
    client = BrainMqttClient(host="localhost", port=1883, client_id="test")
    captured: dict = {}

    async def fake_publish(topic, payload, *, qos=None, retain=False):
        captured["topic"] = topic
        captured["payload"] = payload

    client.publish = fake_publish  # type: ignore[method-assign]
    return client, captured


def _envelope(**overrides) -> ChimeraEnvelope:
    fields = {"node": "pc-main", "verb": "cmd", "action": "get_battery"}
    fields.update(overrides)
    return ChimeraEnvelope(**fields)


def test_publish_then_verify_round_trip() -> None:
    client, captured = _make_capturing_client()
    envelope = _envelope()

    signed = asyncio.run(publish_envelope(client, "chimera/pc-main/cmd", envelope, KEY))

    assert captured["topic"] == "chimera/pc-main/cmd"
    verified = verify_payload(captured["payload"], KEY)
    assert verified is not None
    assert verified == signed


def test_publish_then_verify_survives_real_json_round_trip() -> None:
    """Closes the canonicalization/serialization question Milestone 1's
    retrospective asked to see proven, not assumed: the actual
    json.dumps/json.loads hop (not just an in-memory dict), including the
    RiskTier enum surviving the trip."""
    client, captured = _make_capturing_client()
    envelope = _envelope(risk=RiskTier.LOW)

    asyncio.run(publish_envelope(client, "chimera/pc-main/cmd", envelope, KEY))

    wire = json.loads(json.dumps(captured["payload"], separators=(",", ":")))
    assert wire["risk"] == "low"  # plain string on the wire, not the enum

    verified = verify_payload(wire, KEY)
    assert verified is not None
    assert verified.risk is RiskTier.LOW


def test_tampered_payload_fails_verification() -> None:
    client, captured = _make_capturing_client()
    asyncio.run(publish_envelope(client, "chimera/pc-main/cmd", _envelope(), KEY))

    tampered = {**captured["payload"], "action": "wipe_disk"}
    assert verify_payload(tampered, KEY) is None


def test_expired_timestamp_fails_verification() -> None:
    client, captured = _make_capturing_client()
    asyncio.run(publish_envelope(client, "chimera/pc-main/cmd", _envelope(), KEY))

    stale = {**captured["payload"], "ts": captured["payload"]["ts"] - 121}
    assert verify_payload(stale, KEY) is None


def test_wrong_key_fails_verification() -> None:
    client, captured = _make_capturing_client()
    asyncio.run(publish_envelope(client, "chimera/pc-main/cmd", _envelope(), KEY))

    assert verify_payload(captured["payload"], "0" * 64) is None


def test_verify_payload_rejects_malformed_dict_without_raising() -> None:
    # Missing required fields (node, verb).
    assert verify_payload({"action": "ping"}, KEY) is None
    # Unexpected extra field -- exercises ChimeraEnvelope's extra="forbid"
    # through the non-raising contract, not a bare model_validate() call.
    assert verify_payload(
        {"node": "pc-main", "verb": "cmd", "smuggled": "evil"}, KEY
    ) is None


def test_publish_envelope_signs_before_publishing() -> None:
    client, captured = _make_capturing_client()
    asyncio.run(publish_envelope(client, "chimera/pc-main/cmd", _envelope(), KEY))

    assert captured["payload"]["sig"] != ""
