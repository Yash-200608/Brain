"""Capabilities handler -- wires an inbound chimera/+/capabilities MQTT
message to DeviceStore.record_capabilities() (Priority #4 Milestone 4).
Parallel consumer to presence.py (Priority #3 Milestone 5) and state.py
(Milestone 7); this is the Brain-side half of Milestone 3's node-side
SkillRegistry/publish_capabilities().

Lives in mqtt/, not devices/, for the same reason as presence.py/state.py:
devices/ stays MQTT- and envelope-agnostic by design.
"""

from __future__ import annotations

import logging

from devices.store import DeviceStore
from mqtt.client import Handler, JsonDict
from mqtt.signed import verify_payload

logger = logging.getLogger("mqtt")


def make_capabilities_handler(store: DeviceStore, key: str) -> Handler:
    """Builds a Handler closing over `store` and the HMAC `key`. Verifies
    each inbound message; only a validly-signed envelope with
    verb == "capabilities" and a `params["skills"]` that is actually a
    list of strings updates the store -- unlike state.py's fully opaque
    params, a capability declaration is exactly what NP-5 / Brain's
    planner needs to be a *list of skill names*, so this handler enforces
    that minimal shape rather than persisting arbitrary params blindly.
    Never raises -- verification, verb-mismatch, or shape failures are
    logged at debug and dropped.
    """

    async def _handle_capabilities(topic: str, payload: JsonDict) -> None:
        envelope = verify_payload(payload, key)
        if envelope is None:
            logger.debug(
                "capabilities message on %r failed verification -- dropping", topic
            )
            return
        if envelope.verb != "capabilities":
            logger.debug(
                "message on %r has verb %r, expected 'capabilities' -- dropping",
                topic,
                envelope.verb,
            )
            return
        skills = envelope.params.get("skills")
        if not isinstance(skills, list) or not all(isinstance(s, str) for s in skills):
            logger.debug(
                "capabilities message on %r has a malformed 'skills' field -- dropping",
                topic,
            )
            return
        store.record_capabilities(envelope.node, skills)

    return _handle_capabilities
