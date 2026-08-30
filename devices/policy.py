"""Brain-side skill risk policy (Priority #4 Milestone 7).

Assigns the planner-facing risk int (0=safe / 1=ask-nothing-but-notable /
2=approval-required -- the pervasive Task.risk representation) to a device
skill name. This is Brain's AUTHORIZATION policy, authority-assigned per
NP-6 -- it is never read from an envelope, a node declaration, or any
caller input. It is deliberately independent of the node-side kernel's
own classification (root core/'s TOOLS table): the node's kernel and
operator ceiling are the last line of defense (NP-8); this policy is the
first. The two do not need to agree -- each fails closed on its own.

Fail-closed: any skill this policy does not recognize is risk 2
(approval-required), never lower. RiskTier.from_legacy_int() converts at
the envelope boundary when needed.
"""

from __future__ import annotations

# Exact-match table first, then prefix rules, then fail-closed 2.
_EXACT: dict[str, int] = {
    "ping": 0,
    "phone.battery": 0,
    "phone.location": 1,  # sensitive read: notable, not approval-gated
    "phone.tts": 1,
    "phone.notify": 1,
    "phone.torch": 1,
    "phone.vibrate": 1,
    "phone.ring": 1,
    "phone.app.open": 1,
    "phone.sms.send": 1,
    "phone.whatsapp.send": 1,
    "pc.system.lock": 1,
    "pc.media.control": 1,
    "pc.shell.run": 2,
}

_PREFIX_RULES: list[tuple[str, int]] = [
    # Any future *.send stays at least notable; shell/delete/shutdown
    # anywhere in a skill name is approval-required.
]


def skill_risk_int(skill: str) -> int:
    """0/1/2 for `skill`; unknown skills are 2 (fail-closed, NP-3)."""
    if skill in _EXACT:
        return _EXACT[skill]
    lowered = skill.lower()
    if any(tok in lowered for tok in ("shell", "delete", "shutdown", "wipe", "kill")):
        return 2
    return 2  # unknown -> approval-required, never permissive


# Brain-side MQTT round-trip wait — must cover the node skill's own subprocess
# timeout (e.g. phone.tts allows 60s on the node). Default 15s for fast skills.
_SKILL_DISPATCH_TIMEOUT: dict[str, float] = {
    "phone.tts": 65.0,
    "phone.location": 35.0,
    "phone.ring": 70.0,
}


def skill_dispatch_timeout(skill: str, default: float = 15.0) -> float:
    """Seconds Brain waits for a signed spine response for `skill`."""
    return _SKILL_DISPATCH_TIMEOUT.get(skill, default)
