"""Proves Brain's side of the first command/response round trip
(Priority #3 Milestone 6): signs a "cmd" envelope with Brain's real
sign(), then separately hand-builds a "response" envelope simulating
correct JARVIS behavior (verified against JARVIS's real code in JARVIS's
own test suite -- see jarvis_node_sdk/tests/test_command_handler.py),
signs it with Brain's own sign() (same key), and verifies it via
verify_payload() -- proving Brain can produce a valid command and consume
a valid response using only its own real production code.

No live broker, no cross-repo import of JARVIS's code.
"""

from __future__ import annotations

from mqtt.signed import verify_payload
from protocols.chimera_contract import ChimeraEnvelope, sign

KEY = "f" * 64
NODE = "jarvis-core-pc"


def test_brain_signs_cmd_and_verifies_hand_built_response() -> None:
    cmd = ChimeraEnvelope(node=NODE, verb="cmd", action="ping")
    signed_cmd = sign(cmd, KEY)
    assert signed_cmd.sig != ""

    # Simulates the response a correctly-behaving JARVIS handler would
    # produce (proven for real in jarvis_node_sdk's own test suite).
    response = ChimeraEnvelope(
        node=NODE, verb="response", action="ping", params={"pong": True}
    )
    signed_response = sign(response, KEY)

    verified = verify_payload(signed_response.model_dump(), KEY)
    assert verified is not None
    assert verified.params == {"pong": True}


def test_tampered_response_fails_verification() -> None:
    response = ChimeraEnvelope(
        node=NODE, verb="response", action="ping", params={"pong": True}
    )
    signed_response = sign(response, KEY)
    tampered = {**signed_response.model_dump(), "params": {"pong": False}}

    assert verify_payload(tampered, KEY) is None


def test_response_with_wrong_verb_still_verifies_but_caller_must_check_it() -> None:
    """verify_payload() only checks the signature -- it doesn't know what
    verb a caller expects. This documents that callers awaiting a
    "response" must check envelope.verb themselves (matching the pattern
    mqtt/presence.py's handler already establishes for "cmd" dispatch)."""
    mismatched = ChimeraEnvelope(
        node=NODE, verb="event", action="ping", params={"pong": True}
    )
    signed = sign(mismatched, KEY)

    verified = verify_payload(signed.model_dump(), KEY)
    assert verified is not None
    assert verified.verb != "response"
