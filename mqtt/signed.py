"""Signed-envelope/MQTT composition layer (Priority #3 Milestone 3).

Proves that protocols/chimera_contract.py's ChimeraEnvelope (Milestone 1)
and mqtt/client.py's BrainMqttClient (Milestone 2) compose correctly --
BrainMqttClient stays deliberately envelope-agnostic by its own docstring's
design commitment, so this thin module is where the two meet.

Does NOT do: topic construction (callers pass literal topic strings; no
real call site exists yet to design a builder against), EventBus wiring,
Device Registry, or anything involving a live broker.
"""

from __future__ import annotations

from pydantic import ValidationError

from mqtt.client import BrainMqttClient
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
