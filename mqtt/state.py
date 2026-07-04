"""State handler -- wires an inbound chimera/+/state MQTT message to
DeviceStore.record_state(). Parallel consumer to presence.py (Priority #3
Milestone 5); this is Milestone 7.

Lives in mqtt/, not devices/, for the same reason as presence.py: devices/
stays MQTT- and envelope-agnostic by design.
"""

from __future__ import annotations

import logging

from devices.store import DeviceStore
from mqtt.client import Handler, JsonDict
from mqtt.signed import verify_payload

logger = logging.getLogger("mqtt")


def make_state_handler(store: DeviceStore, key: str) -> Handler:
    """Builds a Handler closing over `store` and the HMAC `key`. Verifies
    each inbound message; only a validly-signed envelope with
    verb == "state" updates the store. The envelope's `params` dict is
    persisted opaquely -- no schema is imposed on its contents (see
    Milestone 7 plan). Never raises -- verification or verb-mismatch
    failures are logged at debug and dropped.
    """

    async def _handle_state(topic: str, payload: JsonDict) -> None:
        envelope = verify_payload(payload, key)
        if envelope is None:
            logger.debug("state message on %r failed verification -- dropping", topic)
            return
        if envelope.verb != "state":
            logger.debug(
                "message on %r has verb %r, expected 'state' -- dropping",
                topic,
                envelope.verb,
            )
            return
        store.record_state(envelope.node, envelope.params)

    return _handle_state
