"""State handler unit tests -- mqtt.state.make_state_handler.

Mirrors test_mqtt_presence.py's real-envelope-signing technique and
test_devices.py's tempfile-backed DeviceStore convention. No live broker,
no mocked verify_payload -- exercises the real sign()/verify_payload()
round trip so a signature-format regression in either would be caught
here too.
"""

from __future__ import annotations

import asyncio
import tempfile

from devices.store import DeviceStore
from mqtt.state import make_state_handler
from protocols.chimera_contract import ChimeraEnvelope, sign

KEY = "f" * 64


def _make_store() -> DeviceStore:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    return DeviceStore(db_path=db)


def _signed_state_payload(node: str, params: dict, **overrides) -> dict:
    fields = {"node": node, "verb": "state", "params": params}
    fields.update(overrides)
    envelope = ChimeraEnvelope(**fields)
    signed = sign(envelope, KEY)
    return signed.model_dump()


def test_valid_state_updates_device_store() -> None:
    store = _make_store()
    handler = make_state_handler(store, KEY)
    payload = _signed_state_payload("pc-main", {"battery_pct": 87})

    asyncio.run(handler("chimera/pc-main/state", payload))

    device = store.get("pc-main")
    assert device is not None
    assert device.state == {"battery_pct": 87}


def test_tampered_payload_does_not_update_store() -> None:
    store = _make_store()
    handler = make_state_handler(store, KEY)
    payload = _signed_state_payload("pc-main", {"battery_pct": 87})
    tampered = {**payload, "params": {"battery_pct": 0}}

    asyncio.run(handler("chimera/pc-main/state", tampered))

    assert store.get("pc-main") is None


def test_wrong_key_does_not_update_store() -> None:
    store = _make_store()
    handler = make_state_handler(store, "0" * 64)
    payload = _signed_state_payload("pc-main", {"battery_pct": 87})

    asyncio.run(handler("chimera/pc-main/state", payload))

    assert store.get("pc-main") is None


def test_wrong_verb_does_not_update_store() -> None:
    store = _make_store()
    handler = make_state_handler(store, KEY)
    payload = _signed_state_payload("pc-main", {"battery_pct": 87}, verb="presence")

    asyncio.run(handler("chimera/pc-main/state", payload))

    assert store.get("pc-main") is None


def test_malformed_payload_does_not_raise_or_update_store() -> None:
    store = _make_store()
    handler = make_state_handler(store, KEY)

    asyncio.run(handler("chimera/pc-main/state", {"garbage": True}))

    assert store.get("pc-main") is None


def test_empty_params_dict_is_persisted() -> None:
    """An empty {} is a valid report, distinct from None/never-reported."""
    store = _make_store()
    handler = make_state_handler(store, KEY)
    payload = _signed_state_payload("pc-main", {})

    asyncio.run(handler("chimera/pc-main/state", payload))

    device = store.get("pc-main")
    assert device is not None
    assert device.state == {}
