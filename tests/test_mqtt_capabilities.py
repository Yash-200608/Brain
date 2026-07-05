"""Capabilities handler unit tests -- mqtt.capabilities.make_capabilities_handler
(Priority #4 Milestone 4).

Mirrors test_mqtt_state.py's real-envelope-signing technique and
test_devices.py's tempfile-backed DeviceStore convention exactly. No live
broker, no mocked verify_payload -- exercises the real sign()/
verify_payload() round trip.
"""

from __future__ import annotations

import asyncio
import tempfile

from devices.store import DeviceStore
from mqtt.capabilities import make_capabilities_handler
from protocols.chimera_contract import ChimeraEnvelope, sign

KEY = "f" * 64


def _make_store() -> DeviceStore:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = f.name
    return DeviceStore(db_path=db)


def _signed_capabilities_payload(node: str, params: dict, **overrides) -> dict:
    fields = {"node": node, "verb": "capabilities", "params": params}
    fields.update(overrides)
    envelope = ChimeraEnvelope(**fields)
    signed = sign(envelope, KEY)
    return signed.model_dump()


def test_valid_capabilities_updates_device_store() -> None:
    store = _make_store()
    handler = make_capabilities_handler(store, KEY)
    payload = _signed_capabilities_payload("pc-main", {"skills": ["pc.system.lock"]})

    asyncio.run(handler("chimera/pc-main/capabilities", payload))

    device = store.get("pc-main")
    assert device is not None
    assert device.skills == ["pc.system.lock"]


def test_tampered_payload_does_not_update_store() -> None:
    store = _make_store()
    handler = make_capabilities_handler(store, KEY)
    payload = _signed_capabilities_payload("pc-main", {"skills": ["pc.system.lock"]})
    tampered = {**payload, "params": {"skills": ["pc.shell.run"]}}

    asyncio.run(handler("chimera/pc-main/capabilities", tampered))

    assert store.get("pc-main") is None


def test_wrong_key_does_not_update_store() -> None:
    store = _make_store()
    handler = make_capabilities_handler(store, "0" * 64)
    payload = _signed_capabilities_payload("pc-main", {"skills": ["pc.system.lock"]})

    asyncio.run(handler("chimera/pc-main/capabilities", payload))

    assert store.get("pc-main") is None


def test_wrong_verb_does_not_update_store() -> None:
    store = _make_store()
    handler = make_capabilities_handler(store, KEY)
    payload = _signed_capabilities_payload(
        "pc-main", {"skills": ["pc.system.lock"]}, verb="state"
    )

    asyncio.run(handler("chimera/pc-main/capabilities", payload))

    assert store.get("pc-main") is None


def test_malformed_payload_does_not_raise_or_update_store() -> None:
    store = _make_store()
    handler = make_capabilities_handler(store, KEY)

    asyncio.run(handler("chimera/pc-main/capabilities", {"garbage": True}))

    assert store.get("pc-main") is None


def test_missing_skills_key_does_not_update_store() -> None:
    """A validly-signed capabilities envelope whose params has no 'skills'
    key at all must be dropped, not crash or persist a None/garbage value."""
    store = _make_store()
    handler = make_capabilities_handler(store, KEY)
    payload = _signed_capabilities_payload("pc-main", {"unrelated": True})

    asyncio.run(handler("chimera/pc-main/capabilities", payload))

    assert store.get("pc-main") is None


def test_non_string_skill_entries_do_not_update_store() -> None:
    """A 'skills' value that is a list but contains non-string entries must
    be rejected -- NP-5 requires this to be a list of skill *names*."""
    store = _make_store()
    handler = make_capabilities_handler(store, KEY)
    payload = _signed_capabilities_payload("pc-main", {"skills": ["ok", 123]})

    asyncio.run(handler("chimera/pc-main/capabilities", payload))

    assert store.get("pc-main") is None


def test_empty_skills_list_is_persisted() -> None:
    """An empty [] is a valid declaration ("no skills right now"), distinct
    from None/never-declared."""
    store = _make_store()
    handler = make_capabilities_handler(store, KEY)
    payload = _signed_capabilities_payload("pc-main", {"skills": []})

    asyncio.run(handler("chimera/pc-main/capabilities", payload))

    device = store.get("pc-main")
    assert device is not None
    assert device.skills == []
