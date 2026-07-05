"""Deterministic device-intent mapper (Priority #4 Milestone 7).

Maps a natural-language request onto a (skill, params) pair for the
keystone demo's confirmed command classes -- deterministically, BEFORE the
LLM planner, per the frozen definition's Risk R2 mitigation ("add a
deterministic intent-to-skill mapping layer for the confirmed list with
LLM fallback"): the daily commands the retirement trial hinges on must
not depend on LLM parse luck. Anything this mapper does not match falls
through to the normal cognitive pipeline unchanged.

Node selection does NOT happen here -- the mapper names a skill; the
dispatcher resolves which node currently declares it from live
declarations (NP-5).

The mapping itself IS planning (deciding what should happen), which is
exactly why it lives in Brain's core/ and nowhere near a node (NP-1).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from devices.policy import skill_risk_int


@dataclass
class DeviceIntent:
    skill: str
    params: dict
    risk: int  # planner-facing int, from devices.policy (authority-assigned)


def _intent(skill: str, params: dict | None = None) -> DeviceIntent:
    return DeviceIntent(skill=skill, params=params or {}, risk=skill_risk_int(skill))


_PHONE_HINT = r"(?:on |my |the )*phone"

# Ordered rules: first match wins. Kept deliberately narrow -- a missed
# match falls through to the LLM pipeline, a wrong match would dispatch a
# device action the user didn't ask for, so precision beats recall here.
_RULES: list[tuple[re.Pattern, "callable"]] = []


def _rule(pattern: str):
    def deco(fn):
        _RULES.append((re.compile(pattern, re.IGNORECASE), fn))
        return fn

    return deco


@_rule(r"\b(battery|juice|charge level|phone dying)\b")
def _battery(m: re.Match, text: str) -> DeviceIntent:
    return _intent("phone.battery")


@_rule(r"\b(?:send|shoot|text)\b.*\bwhatsapp\b|\bwhatsapp\b.*\b(?:send|message|text)\b")
def _whatsapp(m: re.Match, text: str) -> DeviceIntent | None:
    return _messaging_intent("phone.whatsapp.send", text)


@_rule(r"\b(?:send|shoot)\b.*\b(?:sms|text message)\b|\b(?:sms|text)\b +\+?\d")
def _sms(m: re.Match, text: str) -> DeviceIntent | None:
    return _messaging_intent("phone.sms.send", text)


@_rule(r"\bopen\b\s+(?P<app>[a-z0-9_.]+)\s+" + _PHONE_HINT + r"|\bopen\b\s+(?P<app2>[a-z0-9_.]+)\s+on my phone")
def _open_app(m: re.Match, text: str) -> DeviceIntent:
    app = m.group("app") or m.group("app2")
    return _intent("phone.app.open", {"app": app})


@_rule(r"\b(?:notify|remind)\b.*" + _PHONE_HINT + r"|\bphone notification\b")
def _notify(m: re.Match, text: str) -> DeviceIntent:
    return _intent("phone.notify", {"title": "JARVIS", "content": text})


@_rule(r"\b(?:say|speak|announce)\b\s+[\"'](?P<text>[^\"']+)[\"']")
def _tts(m: re.Match, text: str) -> DeviceIntent:
    return _intent("phone.tts", {"text": m.group("text")})


@_rule(r"\block\b.*\b(?:pc|computer|workstation|desktop)\b|\b(?:pc|computer)\b.*\block\b")
def _lock_pc(m: re.Match, text: str) -> DeviceIntent:
    return _intent("pc.system.lock")


@_rule(r"\b(?:pause|play)\b.*\b(?:music|song|media|that)\b|\bplay.?pause\b")
def _media_play(m: re.Match, text: str) -> DeviceIntent:
    return _intent("pc.media.control", {"command": "play_pause"})


@_rule(r"\b(?:volume up|louder|crank it)\b")
def _vol_up(m: re.Match, text: str) -> DeviceIntent:
    return _intent("pc.media.control", {"command": "volume_up"})


@_rule(r"\b(?:volume down|quieter|quiet down)\b")
def _vol_down(m: re.Match, text: str) -> DeviceIntent:
    return _intent("pc.media.control", {"command": "volume_down"})


@_rule(r"\b(?:mute)\b")
def _mute(m: re.Match, text: str) -> DeviceIntent:
    return _intent("pc.media.control", {"command": "mute"})


@_rule(r"\b(?:run|execute)\b\s+(?:shell|command|cmd)\b\s*[:]?\s*(?P<cmd>.+)$")
def _shell(m: re.Match, text: str) -> DeviceIntent:
    # risk 2 by policy -- always lands in the approval flow, never direct.
    return _intent("pc.shell.run", {"command": m.group("cmd").strip()})


_RECIPIENT_MSG = re.compile(
    r"(?:to|tell)\s+(?P<recipient>\+?\w[\w\s+]*?)\s*(?:that|:|,)\s*(?P<message>.+)$",
    re.IGNORECASE,
)


def _messaging_intent(skill: str, text: str) -> DeviceIntent | None:
    m = _RECIPIENT_MSG.search(text)
    if not m:
        return None  # can't extract recipient+message deterministically -> LLM fallback
    return _intent(
        skill,
        {"phone": m.group("recipient").strip(), "message": m.group("message").strip()},
    )


def map_device_intent(text: str) -> DeviceIntent | None:
    """The confirmed-command-class mapper. Returns None (LLM fallback) for
    anything it cannot map with confidence."""
    stripped = text.strip()
    if not stripped:
        return None
    for pattern, fn in _RULES:
        m = pattern.search(stripped)
        if m:
            intent = fn(m, stripped)
            if intent is not None:
                return intent
    return None
