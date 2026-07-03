"""Presence handler -- wires an inbound chimera/+/presence MQTT message to
DeviceStore.mark_seen(). First real consumer of mqtt/client.py's wildcard
dispatch (Priority #3 Milestone 5).

Lives in mqtt/, not devices/: devices/store.py and devices/models.py have
zero MQTT or envelope awareness by design (DeviceStore must stay usable
with MQTT disabled), so the composition point belongs here, alongside
signed.py -- the other module that bridges chimera_contract and
BrainMqttClient.
"""

from __future__ import annotations

import logging

from devices.store import DeviceStore
from mqtt.client import Handler, JsonDict
from mqtt.signed import verify_payload

logger = logging.getLogger("mqtt")


def make_presence_handler(store: DeviceStore, key: str) -> Handler:
    """Builds a Handler closing over `store` and the HMAC `key`. Verifies
    each inbound message; only a validly-signed envelope with
    verb == "presence" updates the store. Never raises -- verification or
    verb-mismatch failures are logged at debug and dropped.
    """

    async def _handle_presence(topic: str, payload: JsonDict) -> None:
        envelope = verify_payload(payload, key)
        if envelope is None:
            logger.debug("presence message on %r failed verification -- dropping", topic)
            return
        if envelope.verb != "presence":
            logger.debug(
                "message on %r has verb %r, expected 'presence' -- dropping",
                topic,
                envelope.verb,
            )
            return
        store.mark_seen(envelope.node)

    return _handle_presence
