"""Presence handler unit tests -- mqtt.presence.make_presence_handler.

Mirrors test_mqtt_signed.py's real-envelope-signing technique and
test_devices.py's tempfile-backed DeviceStore convention. No live broker,
no mocked verify_payload -- exercises the real sign()/verify_payload()
round trip so a signature-format regression in either would be caught
here too.
"""

from __future__ import annotations

import asyncio
import tempfile

from devices.store import DeviceStore
from mqtt.presence import make_presence_handler
from protocols.chimera_contract import ChimeraEnvelope, sign

KEY = "f" * 64


def _make_store() -> DeviceStore:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    return DeviceStore(db_path=db)


def _signed_presence_payload(node: str, **overrides) -> dict:
    fields = {"node": node, "verb": "presence"}
    fields.update(overrides)
    envelope = ChimeraEnvelope(**fields)
    signed = sign(envelope, KEY)
    return signed.model_dump()


def test_valid_presence_updates_device_store() -> None:
    store = _make_store()
    handler = make_presence_handler(store, KEY)
    payload = _signed_presence_payload("pc-main")

    asyncio.run(handler("chimera/pc-main/presence", payload))

    device = store.get("pc-main")
    assert device is not None
    assert device.node == "pc-main"


def test_tampered_payload_does_not_update_store() -> None:
    store = _make_store()
    handler = make_presence_handler(store, KEY)
    payload = _signed_presence_payload("pc-main")
    tampered = {**payload, "node": "attacker-node"}

    asyncio.run(handler("chimera/pc-main/presence", tampered))

    assert store.get("pc-main") is None
    assert store.get("attacker-node") is None


def test_wrong_key_does_not_update_store() -> None:
    store = _make_store()
    handler = make_presence_handler(store, "0" * 64)
    payload = _signed_presence_payload("pc-main")

    asyncio.run(handler("chimera/pc-main/presence", payload))

    assert store.get("pc-main") is None


def test_wrong_verb_does_not_update_store() -> None:
    store = _make_store()
    handler = make_presence_handler(store, KEY)
    payload = _signed_presence_payload("pc-main", verb="state")

    asyncio.run(handler("chimera/pc-main/presence", payload))

    assert store.get("pc-main") is None


def test_malformed_payload_does_not_raise_or_update_store() -> None:
    store = _make_store()
    handler = make_presence_handler(store, KEY)

    asyncio.run(handler("chimera/pc-main/presence", {"garbage": True}))

    assert store.get("pc-main") is None
